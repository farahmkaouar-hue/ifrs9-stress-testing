"""
stress_model_comparison.py - Comparaison de moteurs de stress testing.

Ce module separe clairement le stress testing de la logique forward-looking:
plusieurs moteurs concurrents transforment un choc macro en PD/LGD/EAD/ECL
stresses, puis un scoring selectionne le champion.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.stress_scenarios import (
    BASELINE,
    SCENARIO_2008,
    compute_ead_stressed,
    compute_lgd_stressed,
    compute_markov_stage_migration,
    deterministic_pd_lift,
    macro_severity_score,
)

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "outputs" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class StressModelWeights:
    backtesting: float = 0.30
    economic_coherence: float = 0.20
    temporal_stability: float = 0.20
    ecl_precision: float = 0.15
    interpretability: float = 0.15


MODEL_INTERPRETABILITY = {
    "deterministic_sensitivity": 0.95,
    "satellite_macro": 0.70,
    "markov_stage_migration": 0.85,
    "ml_macro_conditioned": 0.55,
    "hybrid_satellite_markov_floor": 0.80,
}


def _baseline_pd(df: pd.DataFrame) -> pd.Series:
    if "PD_pred" in df.columns:
        return df["PD_pred"].fillna(df["PD_pred"].median()).clip(0, 1)
    if "default_flag" in df.columns:
        dr = float(df["default_flag"].mean())
    else:
        dr = 0.05
    return pd.Series(dr, index=df.index, dtype=float)


def _horizon_factor(df: pd.DataFrame, stage_col: str = "stage") -> pd.Series:
    term = df["term_months"].fillna(36) if "term_months" in df.columns else pd.Series(36, index=df.index)
    stage = df[stage_col] if stage_col in df.columns else pd.Series(1, index=df.index)
    return pd.Series(np.where(stage.eq(1), 12.0 / term.clip(1), 1.0), index=df.index)


def _ecl(df: pd.DataFrame, pd_col: str, lgd_col: str, ead_col: str, stage_col: str = "stage") -> pd.Series:
    return (
        df[pd_col].clip(0, 1)
        * df[lgd_col].clip(0, 1)
        * df[ead_col].clip(lower=0)
        * _horizon_factor(df, stage_col)
    )


def _satellite_lift(
    scenario: dict,
    satellite_model=None,
    satellite_features: list[str] | None = None,
    satellite_champion: str = "OLS",
) -> float:
    if satellite_model is None or satellite_features is None:
        return deterministic_pd_lift(scenario)

    try:
        from src.satellite_models import predict_pd_satellite

        dr_base = predict_pd_satellite(BASELINE, satellite_champion, satellite_model, satellite_features)
        dr_stress = predict_pd_satellite(scenario, satellite_champion, satellite_model, satellite_features)
        return float(np.clip(dr_stress / max(dr_base, 1e-6), 0.25, 5.0))
    except Exception:
        return deterministic_pd_lift(scenario)


def run_deterministic_sensitivity(df: pd.DataFrame, scenario: dict) -> pd.DataFrame:
    result = df.copy()
    result["PD_stressed"] = (_baseline_pd(df) * deterministic_pd_lift(scenario)).clip(0, 1)
    result["LGD_stressed"] = compute_lgd_stressed(df, scenario)
    result["EAD_stressed"] = compute_ead_stressed(df, scenario)
    result["ECL_stressed"] = _ecl(result, "PD_stressed", "LGD_stressed", "EAD_stressed")
    return result


def run_satellite_macro(
    df: pd.DataFrame,
    scenario: dict,
    satellite_model=None,
    satellite_features: list[str] | None = None,
    satellite_champion: str = "OLS",
) -> pd.DataFrame:
    result = df.copy()
    lift = max(
        _satellite_lift(scenario, satellite_model, satellite_features, satellite_champion),
        1.0,
    )
    result["PD_stressed"] = (_baseline_pd(df) * lift).clip(0, 1)
    result["LGD_stressed"] = compute_lgd_stressed(df, scenario)
    result["EAD_stressed"] = compute_ead_stressed(df, scenario)
    result["ECL_stressed"] = _ecl(result, "PD_stressed", "LGD_stressed", "EAD_stressed")
    return result


def run_markov_stage_migration(df: pd.DataFrame, scenario: dict, scenario_name: str = "stress") -> pd.DataFrame:
    base = run_deterministic_sensitivity(df, scenario)
    migrated, _, _ = compute_markov_stage_migration(base, scenario, scenario_name)
    result = base.copy()
    result["stage_stressed"] = migrated["stage_stressed"]
    result["ECL_stressed"] = _ecl(result, "PD_stressed", "LGD_stressed", "EAD_stressed", "stage_stressed")
    return result


def run_ml_macro_conditioned(
    df: pd.DataFrame,
    scenario: dict,
    ml_lift_multiplier: float = 1.15,
) -> pd.DataFrame:
    """Proxy challenger ML: lift non-lineaire plus agressif que le plancher expert."""
    result = df.copy()
    severity = macro_severity_score(scenario)
    lift = np.clip(1.0 + ml_lift_multiplier * np.log1p(3.0 * severity), 1.0, 5.0)
    result["PD_stressed"] = (_baseline_pd(df) * lift).clip(0, 1)
    result["LGD_stressed"] = compute_lgd_stressed(df, scenario, alpha=0.075)
    result["EAD_stressed"] = compute_ead_stressed(df, scenario)
    result["ECL_stressed"] = _ecl(result, "PD_stressed", "LGD_stressed", "EAD_stressed")
    return result


def run_hybrid_satellite_markov_floor(
    df: pd.DataFrame,
    scenario: dict,
    scenario_name: str = "stress",
    satellite_model=None,
    satellite_features: list[str] | None = None,
    satellite_champion: str = "OLS",
) -> pd.DataFrame:
    result = df.copy()
    lift = max(
        deterministic_pd_lift(scenario),
        _satellite_lift(scenario, satellite_model, satellite_features, satellite_champion),
    )
    result["PD_stressed"] = (_baseline_pd(df) * np.clip(lift, 1.0, 5.0)).clip(0, 1)
    result["LGD_stressed"] = compute_lgd_stressed(df, scenario)
    result["EAD_stressed"] = compute_ead_stressed(df, scenario)
    migrated, _, _ = compute_markov_stage_migration(result, scenario, scenario_name)
    result["stage_stressed"] = migrated["stage_stressed"]
    result["ECL_stressed"] = _ecl(result, "PD_stressed", "LGD_stressed", "EAD_stressed", "stage_stressed")
    return result


def summarize_stress_model_output(
    model_name: str,
    stressed: pd.DataFrame,
    baseline_ecl: float,
    observed_target_dr: float | None = None,
) -> dict:
    pd_base = _baseline_pd(stressed)
    pd_stressed = stressed["PD_stressed"]
    ecl_stressed = float(stressed["ECL_stressed"].sum())
    dr_stressed = float(pd_stressed.mean())
    observed_error = abs(dr_stressed - observed_target_dr) if observed_target_dr is not None else np.nan
    ecl_lift = ecl_stressed / max(baseline_ecl, 1e-9)
    return {
        "model_name": model_name,
        "ECL_stressed_M$": round(ecl_stressed / 1e6, 3),
        "ECL_lift": round(ecl_lift, 4),
        "PD_baseline_%": round(float(pd_base.mean()) * 100, 3),
        "PD_stressed_%": round(dr_stressed * 100, 3),
        "PD_lift": round(dr_stressed / max(float(pd_base.mean()), 1e-9), 4),
        "LGD_stressed_%": round(float(stressed["LGD_stressed"].mean()) * 100, 3),
        "EAD_stressed_M$": round(float(stressed["EAD_stressed"].sum()) / 1e6, 3),
        "observed_DR_error": round(observed_error, 6) if not np.isnan(observed_error) else np.nan,
        "economic_coherent": bool(ecl_lift >= 1.0 and dr_stressed >= float(pd_base.mean())),
    }


def score_stress_models(
    comparison: pd.DataFrame,
    weights: StressModelWeights = StressModelWeights(),
) -> pd.DataFrame:
    scored = comparison.copy()

    max_error = scored["observed_DR_error"].dropna().max()
    if np.isnan(max_error) or max_error == 0:
        scored["backtesting_score"] = 0.70
    else:
        scored["backtesting_score"] = 1.0 - (scored["observed_DR_error"] / max_error).clip(0, 1)

    scored["economic_score"] = scored["economic_coherent"].astype(float)
    scored["temporal_stability_score"] = np.where(scored["ECL_lift"].between(1.0, 4.0), 0.85, 0.45)
    scored["ecl_precision_score"] = scored["backtesting_score"]
    scored["interpretability_score"] = scored["model_name"].map(MODEL_INTERPRETABILITY).fillna(0.60)

    scored["final_score"] = (
        weights.backtesting * scored["backtesting_score"]
        + weights.economic_coherence * scored["economic_score"]
        + weights.temporal_stability * scored["temporal_stability_score"]
        + weights.ecl_precision * scored["ecl_precision_score"]
        + weights.interpretability * scored["interpretability_score"]
    )
    return scored.sort_values("final_score", ascending=False)


def compare_stress_testing_models(
    df: pd.DataFrame,
    scenario: dict = SCENARIO_2008,
    scenario_name: str = "crisis_2008",
    observed_target_dr: float | None = None,
    satellite_model=None,
    satellite_features: list[str] | None = None,
    satellite_champion: str = "OLS",
    save: bool = True,
) -> tuple[pd.DataFrame, str]:
    """
    Execute les moteurs concurrents, score les resultats et retourne le champion.

    observed_target_dr peut etre le taux de defaut realise pendant une crise
    historique. Si absent, on utilise DRCCLACBS du scenario comme proxy.
    """
    if observed_target_dr is None:
        observed_target_dr = scenario.get("DRCCLACBS", np.nan) / 100.0
        if np.isnan(observed_target_dr):
            observed_target_dr = None

    baseline = df.copy()
    baseline["PD_base_tmp"] = _baseline_pd(df)
    baseline["LGD_base_tmp"] = df["LGD"]
    baseline["EAD_base_tmp"] = df["EAD"]
    baseline_ecl = float(_ecl(baseline, "PD_base_tmp", "LGD_base_tmp", "EAD_base_tmp").sum())

    outputs = {
        "deterministic_sensitivity": run_deterministic_sensitivity(df, scenario),
        "satellite_macro": run_satellite_macro(
            df, scenario, satellite_model, satellite_features, satellite_champion
        ),
        "markov_stage_migration": run_markov_stage_migration(df, scenario, scenario_name),
        "ml_macro_conditioned": run_ml_macro_conditioned(df, scenario),
        "hybrid_satellite_markov_floor": run_hybrid_satellite_markov_floor(
            df, scenario, scenario_name, satellite_model, satellite_features, satellite_champion
        ),
    }

    comparison = pd.DataFrame([
        summarize_stress_model_output(name, stressed, baseline_ecl, observed_target_dr)
        for name, stressed in outputs.items()
    ])
    scored = score_stress_models(comparison)
    champion = str(scored.iloc[0]["model_name"])

    if save:
        scored.to_csv(RESULTS_DIR / "stress_model_comparison.csv", index=False)
        pd.DataFrame([{
            "champion_model": champion,
            "scenario_name": scenario_name,
            "selection_rule": "max final_score",
            "observed_target_dr": observed_target_dr,
        }]).to_csv(RESULTS_DIR / "stress_model_champion.csv", index=False)

    return scored, champion
