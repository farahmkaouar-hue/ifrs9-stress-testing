"""
scenario_projection.py - Projections dynamiques IFRS 9 / stress testing.

Ce module transforme un choc statique T0 en trajectoire pluriannuelle:
macro -> PD/LGD/EAD -> migration IFRS 9 -> ECL -> CET1.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path

from src.resilience import CET1_INITIAL
from src.banking_core import enrich_banking_view
from src.stress_scenarios import (
    BASELINE,
    apply_stress,
    compute_markov_stage_migration,
    macro_severity_score,
)

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "outputs" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


MACRO_VARIABLES = [
    "UNRATE",
    "GDPC1_growth",
    "FEDFUNDS",
    "HY_SPREAD",
    "CPI_change",
    "DRCCLACBS",
]


def _shock_multiplier(year: int, horizon_years: int, profile: str) -> float:
    """Renvoie l'intensite du choc pour une annee projetee."""
    if horizon_years <= 1:
        return 1.0

    if profile == "front_loaded":
        return float(np.interp(year, [1, horizon_years], [1.0, 0.45]))
    if profile == "delayed_peak":
        midpoint = max(2, int(np.ceil(horizon_years / 2)))
        if year <= midpoint:
            return float(np.interp(year, [1, midpoint], [0.45, 1.0]))
        return float(np.interp(year, [midpoint, horizon_years], [1.0, 0.55]))
    if profile == "recovery":
        return float(np.interp(year, [1, horizon_years], [1.0, 0.20]))

    return float(year / horizon_years)


def build_scenario_path(
    target_scenario: dict,
    horizon_years: int = 3,
    profile: str = "front_loaded",
    baseline: dict = BASELINE,
) -> pd.DataFrame:
    """
    Construit une trajectoire annuelle entre baseline et scenario cible.

    profile:
    - front_loaded: choc maximal des T1 puis normalisation progressive.
    - linear: montee lineaire vers le choc cible.
    - delayed_peak: choc qui culmine au milieu de l'horizon.
    - recovery: choc fort en T1 puis retour rapide vers baseline.
    """
    horizon_years = int(max(1, horizon_years))
    rows = []
    for year in range(1, horizon_years + 1):
        multiplier = _shock_multiplier(year, horizon_years, profile)
        row = {"year": year, "shock_multiplier": round(multiplier, 4)}
        for variable in MACRO_VARIABLES:
            base_value = float(baseline.get(variable, 0.0))
            target_value = float(target_scenario.get(variable, base_value))
            row[variable] = base_value + multiplier * (target_value - base_value)
        row["severity_score"] = macro_severity_score(row, baseline)
        rows.append(row)
    return pd.DataFrame(rows)


def _stage_adjusted_ecl(df_projected: pd.DataFrame) -> pd.Series:
    term_months = df_projected.get(
        "term_months", pd.Series(36, index=df_projected.index)
    ).fillna(36)
    horizon_factor = np.where(
        df_projected["stage"] == 1,
        12.0 / term_months.clip(lower=1),
        1.0,
    )
    return (
        df_projected["PD_pred"].clip(0, 1)
        * df_projected["LGD"].clip(0, 1)
        * df_projected["EAD"].clip(lower=0)
        * horizon_factor
    )


def compute_dynamic_projection(
    df: pd.DataFrame,
    target_scenario: dict,
    champion_pd_model=None,
    features: list[str] | None = None,
    satellite_pd_model: dict | None = None,
    satellite_pd_features: list[str] | None = None,
    satellite_pd_champion: str = "OLS",
    horizon_years: int = 3,
    profile: str = "front_loaded",
    cet1_initial: float = CET1_INITIAL,
    tax_rate: float = 0.30,
    annual_amortization: float = 0.08,
    use_regulatory_rwa: bool = True,
    save: bool = False,
    scenario_name: str = "custom",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Projette le portefeuille annee par annee sous une trajectoire macro.

    La projection est recursive: les PD/LGD/EAD et stages projetes a T1
    deviennent le point de depart de T2, ce qui evite le simple calcul total.
    """
    features = features or []
    satellite_pd_model = satellite_pd_model or {}
    satellite_pd_features = satellite_pd_features or []

    path = build_scenario_path(target_scenario, horizon_years, profile)
    state = df.copy()
    state["PD_pred"] = state.get("PD_pred", pd.Series(0.03, index=state.index)).astype(float)
    state["stage"] = state.get("stage", pd.Series(1, index=state.index)).astype(int)
    if "ECL_ifrs9" in state.columns:
        state["ECL_ifrs9"] = state["ECL_ifrs9"].astype(float)
    else:
        state["ECL_ifrs9"] = _stage_adjusted_ecl(state).astype(float)
    base_pd = state["PD_pred"].copy()
    base_lgd = state["LGD"].copy()

    if use_regulatory_rwa:
        state, _ = enrich_banking_view(state)

    initial_ead_m = state["EAD"].sum() / 1e6
    initial_rwa_m = state["RWA"].sum() / 1e6 if "RWA" in state.columns else initial_ead_m
    initial_ecl_m = state["ECL_ifrs9"].sum() / 1e6
    capital_m = cet1_initial * initial_rwa_m
    previous_ecl_m = initial_ecl_m
    previous_stage = state["stage"].copy()

    portfolio_rows = []
    stage_rows = []

    for _, macro_row in path.iterrows():
        year = int(macro_row["year"])
        scenario_t = {var: float(macro_row[var]) for var in MACRO_VARIABLES}

        stress_input = state.copy()
        # Les projections bancaires ne doivent pas multiplier une PD/LGD deja
        # stressee a chaque annee. On garde la dynamique des stages/EAD/capital,
        # mais on recalcule les parametres de risque depuis la reference.
        stress_input["PD_pred"] = base_pd
        stress_input["LGD"] = base_lgd

        stressed = apply_stress(
            stress_input,
            scenario_t,
            f"{scenario_name}_Y{year}",
            champion_pd_model,
            features,
            satellite_pd_model,
            satellite_pd_features,
            satellite_pd_champion,
            enforce_ecl_floor=False,
        )

        migrated, migration_stats, _ = compute_markov_stage_migration(
            stressed.assign(stage=state["stage"]),
            scenario_t,
            f"{scenario_name}_Y{year}",
        )

        projected = state.copy()
        projected["PD_pred"] = stressed["PD_stressed"].clip(0, 1)
        projected["LGD"] = stressed["LGD_stressed"].clip(0, 1)
        projected["EAD"] = (
            stressed["EAD_stressed"] * (1.0 - annual_amortization)
        ).clip(lower=0)
        projected["stage"] = migrated["stage_stressed"].astype(int)
        projected["ECL_ifrs9"] = _stage_adjusted_ecl(projected)
        if use_regulatory_rwa:
            projected, _ = enrich_banking_view(projected)

        ead_m = projected["EAD"].sum() / 1e6
        rwa_m = projected["RWA"].sum() / 1e6 if "RWA" in projected.columns else ead_m
        ecl_m = projected["ECL_ifrs9"].sum() / 1e6
        annual_provision_m = max(ecl_m - previous_ecl_m, 0.0)
        capital_m -= annual_provision_m * (1.0 - tax_rate)
        cet1_ratio = capital_m / max(rwa_m, 1e-9)

        stage_dist = projected["stage"].value_counts(normalize=True).reindex([1, 2, 3], fill_value=0)
        stage_rows.append({
            "year": year,
            "Stage 1_%": round(stage_dist.loc[1] * 100, 2),
            "Stage 2_%": round(stage_dist.loc[2] * 100, 2),
            "Stage 3_%": round(stage_dist.loc[3] * 100, 2),
            "migrated_loans": int((projected["stage"] != previous_stage).sum()),
            **migration_stats,
        })

        portfolio_rows.append({
            "year": year,
            "scenario": scenario_name,
            "profile": profile,
            "severity_score": round(float(macro_row["severity_score"]), 4),
            "EAD_M$": round(ead_m, 2),
            "RWA_M$": round(rwa_m, 2),
            "RWA_density_%": round(rwa_m / max(ead_m, 1e-9) * 100, 2),
            "ECL_M$": round(ecl_m, 2),
            "Delta_ECL_vs_T0_M$": round(ecl_m - initial_ecl_m, 2),
            "Annual_provision_M$": round(annual_provision_m, 2),
            "PD_mean_%": round(projected["PD_pred"].mean() * 100, 3),
            "LGD_mean_%": round(projected["LGD"].mean() * 100, 3),
            "CET1_%": round(cet1_ratio * 100, 3),
            "Capital_M$": round(capital_m, 2),
            **{var: round(float(scenario_t[var]), 4) for var in MACRO_VARIABLES},
        })

        state = projected
        previous_ecl_m = ecl_m
        previous_stage = projected["stage"].copy()

    projection = pd.DataFrame(portfolio_rows)
    stage_projection = pd.DataFrame(stage_rows)
    if save:
        projection.to_csv(RESULTS_DIR / "dynamic_projection_summary.csv", index=False)
        stage_projection.to_csv(RESULTS_DIR / "dynamic_stage_projection.csv", index=False)
    return projection, stage_projection
