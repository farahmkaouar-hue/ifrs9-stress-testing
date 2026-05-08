"""
stress_scenarios.py - Definition et application des scenarios de stress IFRS 9.

Scenarios actifs : adverse, severe, choc de taux, marche 2018, crise 2008, COVID-19.
Les scenarios historiques sont calibres sur les variables macro/FRED disponibles.

Usage:
    from src.stress_scenarios import SCENARIOS, ACTIVE_STRESS_SCENARIOS, compute_stress_ecl
"""

import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "outputs" / "models"
RESULTS_DIR = ROOT / "outputs" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Définition des scénarios (valeurs absolues)
# ---------------------------------------------------------------------------

# Valeurs baseline (conditions normales ~2014-2016)
BASELINE = {
    "UNRATE":       4.0,    # %
    "GDPC1_growth": 2.0,    # % YoY
    "FEDFUNDS":     2.5,    # %
    "HY_SPREAD":    3.5,    # %
    "CPI_change":   2.0,    # % YoY
    "DRCCLACBS":    2.5,    # %
}

# Scénario 1 : Choc macroéconomique
SCENARIO_MACRO = {
    "UNRATE":       8.0,    # +4pp
    "GDPC1_growth": -1.5,   # -3.5pp
    "FEDFUNDS":     3.5,    # +1pp (Fed tarde à baisser)
    "HY_SPREAD":    5.5,    # +2pp
    "CPI_change":   3.5,    # +1.5pp
    "DRCCLACBS":    5.0,    # +2.5pp
}

# Scenario adverse intermediaire, utile pour une courbe IFRS 9 base/adverse/severe.
SCENARIO_ADVERSE = {
    "UNRATE":       6.5,
    "GDPC1_growth": -0.5,
    "FEDFUNDS":     3.5,
    "HY_SPREAD":    5.5,
    "CPI_change":   3.0,
    "DRCCLACBS":    4.0,
}

SCENARIO_SEVERE = SCENARIO_MACRO

# Scénario 2 : Choc de taux d'intérêt
SCENARIO_TAUX = {
    "UNRATE":       5.0,    # +1pp
    "GDPC1_growth": 0.5,    # -1.5pp
    "FEDFUNDS":     5.5,    # +3pp
    "HY_SPREAD":    6.5,    # +3pp
    "CPI_change":   5.0,    # +3pp
    "DRCCLACBS":    4.0,    # +1.5pp
}

# Scénario 3 : Choc Combiné 2008 (calibré sur données FRED historiques)
# Valeurs observées au pic de la crise (2009Q1-Q2)
SCENARIO_2008 = {
    "UNRATE":       10.0,   # pic réel Oct 2009
    "GDPC1_growth": -4.3,   # creux réel 2009Q2
    "FEDFUNDS":     0.25,   # plancher Fed 2009
    "HY_SPREAD":    18.5,   # pic spread HY Jan 2009
    "CPI_change":   -0.4,   # déflation 2009
    "DRCCLACBS":    6.77,   # pic délinquance banques 2009
}


SCENARIO_COVID_2020 = {
    "UNRATE":       14.7,
    "GDPC1_growth": -9.0,
    "FEDFUNDS":     0.25,
    "HY_SPREAD":    8.8,
    "CPI_change":   0.2,
    "DRCCLACBS":    3.5,
}

SCENARIO_2018_MARKET = {
    "UNRATE":       3.9,
    "GDPC1_growth": 2.0,
    "FEDFUNDS":     2.4,
    "HY_SPREAD":    5.3,
    "CPI_change":   1.9,
    "DRCCLACBS":    2.5,
}

SCENARIO_UKRAINE_2022 = {
    "UNRATE":       3.7,
    "GDPC1_growth": 1.9,
    "FEDFUNDS":     4.1,
    "HY_SPREAD":    5.7,
    "CPI_change":   8.0,
    "DRCCLACBS":    2.7,
}

# Dictionnaire global des scénarios
SCENARIOS = {
    "baseline":       BASELINE,
    "adverse":        SCENARIO_ADVERSE,
    "severe":         SCENARIO_SEVERE,
    "rate_shock":     SCENARIO_TAUX,
    "crisis_2008":    SCENARIO_2008,
    "covid_2020":     SCENARIO_COVID_2020,
    "market_2018":    SCENARIO_2018_MARKET,
    "ukraine_2022":   SCENARIO_UKRAINE_2022,
}

ACTIVE_STRESS_SCENARIOS = {
    k: SCENARIOS[k]
    for k in ["adverse", "severe", "rate_shock", "market_2018", "ukraine_2022", "crisis_2008", "covid_2020"]
}

SCENARIO_LABELS = {
    "baseline":    "Baseline",
    "adverse":     "Adverse",
    "severe":      "Severe",
    "rate_shock":  "Choc Taux",
    "crisis_2008": "Crise 2008",
    "covid_2020":  "Crise COVID-19",
    "market_2018": "Choc Marche 2018",
    "ukraine_2022": "Inflation Ukraine 2022",
}

SCENARIO_COLORS = {
    "baseline":    "#2ecc71",
    "adverse":     "#f1c40f",
    "severe":      "#d35400",
    "rate_shock":  "#e67e22",
    "crisis_2008": "#e74c3c",
    "covid_2020":  "#8e44ad",
    "market_2018": "#7f8c8d",
    "ukraine_2022": "#c0392b",
}

SCENARIO_ORDER = ["baseline", "adverse", "severe", "rate_shock", "market_2018", "ukraine_2022", "crisis_2008", "covid_2020"]

SCENARIO_NARRATIVES = {
    "adverse": "Ralentissement macroeconomique general avec hausse du chomage et spreads credit.",
    "severe": "Scenario macro severe combinant contraction PIB, chomage eleve et tension credit.",
    "rate_shock": "Hausse brutale des taux et de l'inflation, pression forte sur LGD/EAD.",
    "market_2018": "Stress marche modere centre sur les spreads credit, sans recession profonde.",
    "ukraine_2022": "Choc inflation/geopolitique: taux et prix eleves, tension credit sans choc chomage majeur.",
    "crisis_2008": "Rejeu de la crise financiere mondiale, scenario historique systemique.",
    "covid_2020": "Choc sanitaire extreme, rupture rapide activite/chomage et forte incertitude.",
}

SCENARIO_TYPES = {
    "adverse": "macro",
    "severe": "macro",
    "rate_shock": "taux",
    "market_2018": "marche",
    "ukraine_2022": "geopolitique_inflation",
    "crisis_2008": "historique",
    "covid_2020": "historique",
}


def macro_severity_score(scenario: dict, baseline: dict = BASELINE) -> float:
    """Score metier de severite macro, croissant avec les chocs adverses."""
    components = [
        0.35 * max(scenario.get("UNRATE", baseline["UNRATE"]) - baseline["UNRATE"], 0) / 6.0,
        0.25 * max(baseline["GDPC1_growth"] - scenario.get("GDPC1_growth", baseline["GDPC1_growth"]), 0) / 6.0,
        0.20 * max(scenario.get("HY_SPREAD", baseline["HY_SPREAD"]) - baseline["HY_SPREAD"], 0) / 15.0,
        0.10 * max(scenario.get("DRCCLACBS", baseline["DRCCLACBS"]) - baseline["DRCCLACBS"], 0) / 5.0,
        0.05 * max(scenario.get("FEDFUNDS", baseline["FEDFUNDS"]) - baseline["FEDFUNDS"], 0) / 4.0,
        0.05 * max(scenario.get("CPI_change", baseline["CPI_change"]) - baseline["CPI_change"], 0) / 4.0,
    ]
    return float(np.clip(sum(components), 0.0, 1.5))


def deterministic_pd_lift(scenario: dict, baseline: dict = BASELINE) -> float:
    """Plancher economique de lift PD utilise comme garde-fou du satellite."""
    return float(np.clip(1.0 + 1.8 * macro_severity_score(scenario, baseline), 1.0, 4.0))


def validate_scenario_design(
    scenarios: dict | None = None,
    baseline: dict = BASELINE,
    save: bool = True,
) -> pd.DataFrame:
    """Controle metier des scenarios actifs et sauvegarde le diagnostic."""
    scenarios = scenarios or ACTIVE_STRESS_SCENARIOS
    rows = []
    for name, scenario in scenarios.items():
        if name == "baseline":
            continue
        rows.append({
            "scenario_key": name,
            "scenario": SCENARIO_LABELS.get(name, name),
            "scenario_type": SCENARIO_TYPES.get(name, "custom"),
            "narrative": SCENARIO_NARRATIVES.get(name, ""),
            "UNRATE_delta": scenario.get("UNRATE", baseline["UNRATE"]) - baseline["UNRATE"],
            "GDP_delta": scenario.get("GDPC1_growth", baseline["GDPC1_growth"]) - baseline["GDPC1_growth"],
            "HY_SPREAD_delta": scenario.get("HY_SPREAD", baseline["HY_SPREAD"]) - baseline["HY_SPREAD"],
            "FEDFUNDS_delta": scenario.get("FEDFUNDS", baseline["FEDFUNDS"]) - baseline["FEDFUNDS"],
            "CPI_delta": scenario.get("CPI_change", baseline["CPI_change"]) - baseline["CPI_change"],
            "severity_score": round(macro_severity_score(scenario, baseline), 3),
            "pd_lift_floor": round(deterministic_pd_lift(scenario, baseline), 3),
            "economically_adverse": (
                macro_severity_score(scenario, baseline) > 0
                and (
                    scenario.get("UNRATE", baseline["UNRATE"]) > baseline["UNRATE"]
                    or scenario.get("GDPC1_growth", baseline["GDPC1_growth"]) < baseline["GDPC1_growth"]
                    or scenario.get("HY_SPREAD", baseline["HY_SPREAD"]) > baseline["HY_SPREAD"]
                    or scenario.get("FEDFUNDS", baseline["FEDFUNDS"]) > baseline["FEDFUNDS"]
                    or scenario.get("CPI_change", baseline["CPI_change"]) > baseline["CPI_change"]
                )
            ),
        })
    report = pd.DataFrame(rows)
    if save:
        report.to_csv(RESULTS_DIR / "scenario_design_validation.csv", index=False)
    return report


# ---------------------------------------------------------------------------
# 2. Application des chocs sur PD, LGD, EAD
# ---------------------------------------------------------------------------
def compute_pd_stressed(
    df: pd.DataFrame,
    scenario: dict,
    champion_pd_model,
    features: list[str],
    satellite_model,
    satellite_features: list[str],
    satellite_champion: str = "OLS",
) -> pd.Series:
    """
    Calcule la PD stressée via le modèle satellite.

    Approche :
    1. Prédire DR_stressed via le satellite (taux de défaut agrégé)
    2. Calculer le ratio DR_stressed / DR_baseline (lift)
    3. Appliquer le lift à la PD individuelle prédite

    Returns : Series PD_stressed par prêt
    """
    # PD baseline individuelle. En dashboard, on tolere l'absence du modele
    # pickle si la colonne PD_pred a deja ete calculee par le notebook baseline.
    if champion_pd_model is not None and hasattr(champion_pd_model, "predict_proba") and features:
        available_features = [f for f in features if f in df.columns]
        if available_features:
            X_base = df[available_features].fillna(0)
            pd_base = pd.Series(
                champion_pd_model.predict_proba(X_base)[:, 1],
                index=df.index,
            )
        else:
            pd_base = df.get("PD_pred", pd.Series(0.03, index=df.index)).astype(float)
    else:
        pd_base = df.get("PD_pred", pd.Series(0.03, index=df.index)).astype(float)

    # DR baseline/stressee via satellite. Si le satellite n'est pas disponible,
    # le plancher economique reste actif pour garder un stress coherent.
    model_lift = 1.0
    try:
        from src.satellite_models import predict_pd_satellite

        dr_base = predict_pd_satellite(BASELINE, satellite_champion, satellite_model, satellite_features)
        dr_stress = predict_pd_satellite(scenario, satellite_champion, satellite_model, satellite_features)
        model_lift = dr_stress / max(dr_base, 1e-6)
    except Exception:
        model_lift = 1.0

    # Lift macro
    # Plancher à 1.0 : sous tout scénario adverse, l'ECL ne peut que croître.
    # Cap à 5.0 : évite les valeurs aberrantes en cas de modèle satellite instable.
    floor_lift = deterministic_pd_lift(scenario)
    lift = float(np.clip(max(model_lift, floor_lift), 1.0, 5.0))

    pd_stressed = (pd_base * lift).clip(0, 1)
    return pd_stressed


def compute_pd_stress_diagnostics(
    scenario: dict,
    satellite_model,
    satellite_features: list[str],
    satellite_champion: str = "OLS",
) -> dict:
    """Explique le lift PD retenu pour un scenario."""
    dr_base = np.nan
    dr_stress = np.nan
    model_lift = 1.0
    try:
        from src.satellite_models import predict_pd_satellite

        dr_base = predict_pd_satellite(BASELINE, satellite_champion, satellite_model, satellite_features)
        dr_stress = predict_pd_satellite(scenario, satellite_champion, satellite_model, satellite_features)
        model_lift = dr_stress / max(dr_base, 1e-6)
    except Exception:
        pass
    floor_lift = deterministic_pd_lift(scenario)
    final_lift = float(np.clip(max(model_lift, floor_lift), 1.0, 5.0))
    return {
        "DR_sat_baseline_%": round(dr_base * 100, 3) if not np.isnan(dr_base) else np.nan,
        "DR_sat_stressed_%": round(dr_stress * 100, 3) if not np.isnan(dr_stress) else np.nan,
        "PD_model_lift": round(float(model_lift), 3),
        "PD_floor_lift": round(float(floor_lift), 3),
        "PD_final_lift": round(final_lift, 3),
        "severity_score": round(macro_severity_score(scenario), 3),
    }


def compute_lgd_stressed(
    df: pd.DataFrame,
    scenario: dict,
    baseline: dict = BASELINE,
    alpha: float = 0.06,
) -> pd.Series:
    """
    LGD stressée par formule de sensibilité aux taux.

    LGD_stressed = LGD_base × (1 + α × ΔFEDFUNDS + β × ΔHY_SPREAD)

    α calibré sur la hausse de LGD en 2008 :
    - Scénario adverse : +20-25%
    - Scénario sévère  : +25-35%

    α ≈ 0.06 (par point de taux Fed) et β ≈ 0.01 (par bp spread)
    """
    beta = 0.01
    gamma = 0.015

    delta_fed    = max(scenario.get("FEDFUNDS",  0) - baseline.get("FEDFUNDS",  0), 0)
    delta_spread = max(scenario.get("HY_SPREAD", 0) - baseline.get("HY_SPREAD", 0), 0)
    delta_unrate = max(scenario.get("UNRATE",   0) - baseline.get("UNRATE",   0), 0)

    stress_factor = 1 + alpha * delta_fed + beta * delta_spread + gamma * delta_unrate
    stress_factor = max(stress_factor, 1.0)  # LGD ne peut que croître sous stress

    lgd_stressed = (df["LGD"] * stress_factor).clip(0, 1)
    return lgd_stressed


def compute_ead_stressed(
    df: pd.DataFrame,
    scenario: dict,
    baseline: dict = BASELINE,
) -> pd.Series:
    """
    EAD stressée via un facteur CCF ajusté.

    Sous stress : les emprunteurs en difficulté tirent davantage
    sur leurs lignes de crédit avant le défaut.

    CCF_stressed = 1 + γ × (ΔUNRATE / 10) + δ × (ΔFEDFUNDS / 5)
    γ ≈ 0.10 → +10% EAD pour +10pp de chômage
    δ ≈ 0.05 → +5% EAD pour +5pp de Fed Funds
    """
    gamma = 0.10
    delta = 0.05

    delta_unrate = max(scenario.get("UNRATE",   0) - baseline.get("UNRATE",   0), 0)
    delta_fed    = max(scenario.get("FEDFUNDS", 0) - baseline.get("FEDFUNDS", 0), 0)

    ccf_factor = 1 + gamma * (delta_unrate / 10) + delta * (delta_fed / 5)
    ccf_factor = max(ccf_factor, 1.0)

    ead_stressed = df["EAD"] * ccf_factor
    return ead_stressed


# ---------------------------------------------------------------------------
# 3. Calcul ECL stressée pour un scénario
# ---------------------------------------------------------------------------
def apply_stress(
    df: pd.DataFrame,
    scenario: dict,
    scenario_name: str,
    champion_pd_model,
    features: list[str],
    satellite_pd_model: dict,
    satellite_pd_features: list[str],
    satellite_pd_champion: str = "OLS",
    alpha_lgd: float = 0.06,
    enforce_ecl_floor: bool = True,
) -> pd.DataFrame:
    """
    Applique un scénario de stress au portefeuille et retourne un DataFrame
    enrichi de PD_stressed, LGD_stressed, EAD_stressed, ECL_stressed.
    """
    result = df.copy()

    # PD stressée
    result["PD_stressed"] = compute_pd_stressed(
        df, scenario, champion_pd_model, features,
        satellite_pd_model, satellite_pd_features, satellite_pd_champion
    )

    # LGD stressée
    result["LGD_stressed"] = compute_lgd_stressed(df, scenario, BASELINE, alpha_lgd)

    # EAD stressée
    result["EAD_stressed"] = compute_ead_stressed(df, scenario)

    # Horizon ECL selon stage
    term_months = df.get("term_months", pd.Series(36, index=df.index)).fillna(36)
    horizon_factor = np.where(result["stage"] == 1, 12.0 / term_months.clip(1), 1.0)

    result["ECL_stressed"] = (
        result["PD_stressed"]
        * result["LGD_stressed"]
        * result["EAD_stressed"]
        * horizon_factor
    )
    if enforce_ecl_floor and "ECL_ifrs9" in df.columns and scenario_name != "baseline":
        result["ECL_stressed_raw"] = result["ECL_stressed"]
        result["ECL_stressed"] = np.maximum(result["ECL_stressed"], df["ECL_ifrs9"])
    result["scenario"] = scenario_name

    # Delta ECL
    if "ECL_ifrs9" in df.columns:
        result["ΔECL"] = result["ECL_stressed"] - result["ECL_ifrs9"]
        result["ΔECL_pct"] = (result["ΔECL"] / result["ECL_ifrs9"].replace(0, np.nan)) * 100

    return result


# ---------------------------------------------------------------------------
# 4. Comparaison multi-scénarios
# ---------------------------------------------------------------------------
def compute_stress_ecl(
    df: pd.DataFrame,
    champion_pd_model,
    features: list[str],
    satellite_pd_model: dict,
    satellite_pd_features: list[str],
    satellite_pd_champion: str = "OLS",
    scenarios: dict | None = None,
) -> dict:
    """
    Applique tous les scénarios et retourne un dict {scenario_name: df_stressed}.
    Sauvegarde également un tableau récapitulatif.
    """
    if scenarios is None:
        scenarios = ACTIVE_STRESS_SCENARIOS

    results = {}
    summary = []

    for name, scenario in scenarios.items():
        print(f"\n→ Scénario : {SCENARIO_LABELS.get(name, name)}")
        stressed = apply_stress(
            df, scenario, name, champion_pd_model, features,
            satellite_pd_model, satellite_pd_features, satellite_pd_champion
        )
        results[name] = stressed

        ecl_s  = stressed["ECL_stressed"].sum()
        ecl_b  = df["ECL_ifrs9"].sum() if "ECL_ifrs9" in df.columns else np.nan
        ead_t  = df["EAD"].sum()
        delta  = ecl_s - ecl_b if not np.isnan(ecl_b) else np.nan
        lift   = ecl_s / ecl_b if not np.isnan(ecl_b) and ecl_b > 0 else np.nan

        pd_mean_b  = df.get("PD_pred", pd.Series(dtype=float)).mean()
        pd_mean_s  = stressed["PD_stressed"].mean()
        lgd_mean_s = stressed["LGD_stressed"].mean()
        ead_mean_s = stressed["EAD_stressed"].sum() / 1e9
        pd_diag = compute_pd_stress_diagnostics(
            scenario, satellite_pd_model, satellite_pd_features, satellite_pd_champion
        )

        summary.append({
            "Scenario":        SCENARIO_LABELS.get(name, name),
            "ECL_stressed_M$": round(ecl_s / 1e6, 2),
            "ECL_baseline_M$": round(ecl_b / 1e6, 2) if not np.isnan(ecl_b) else np.nan,
            "ΔECL_M$":         round(delta / 1e6, 2) if not np.isnan(delta) else np.nan,
            "ECL_lift":        round(lift, 2) if not np.isnan(lift) else np.nan,
            "Coverage_%":      round(ecl_s / ead_t * 100, 2),
            "PD_baseline_%":   round(pd_mean_b * 100, 2),
            "PD_stressed_%":   round(pd_mean_s * 100, 2),
            "PD_final_lift":    pd_diag["PD_final_lift"],
            "PD_model_lift":    pd_diag["PD_model_lift"],
            "PD_floor_lift":    pd_diag["PD_floor_lift"],
            "Severity_score":   pd_diag["severity_score"],
            "LGD_stressed_%":  round(lgd_mean_s * 100, 2),
            "EAD_Mrd$":        round(ead_mean_s, 2),
            "Coherent_stress":  bool(lift >= 1.0 and pd_mean_s >= pd_mean_b),
        })

        print(f"  ECL stressed : ${ecl_s/1e6:,.1f} M "
              f"(×{lift:.2f} vs baseline)" if not np.isnan(lift) else
              f"  ECL stressed : ${ecl_s/1e6:,.1f} M")

    summary_df = pd.DataFrame(summary)
    summary_df.to_csv(RESULTS_DIR / "stress_ecl_summary.csv", index=False)
    validate_stress_outputs(summary_df).to_csv(
        RESULTS_DIR / "stress_validation_report.csv", index=False
    )
    print(f"\n✓ Résultats sauvegardés : {RESULTS_DIR / 'stress_ecl_summary.csv'}")

    return results, summary_df


def validate_stress_outputs(summary_df: pd.DataFrame) -> pd.DataFrame:
    """
    Controle que les sorties de stress respectent la logique metier minimale.

    Un scenario adverse doit produire une ECL >= baseline, une PD moyenne >=
    baseline et un lift >= 1. Les exceptions restent visibles dans le rapport.
    """
    rows = []
    for _, row in summary_df.iterrows():
        checks = {
            "ECL_lift_ge_1": row.get("ECL_lift", np.nan) >= 1.0,
            "Delta_ECL_non_negative": row.get("Î”ECL_M$", row.get("ΔECL_M$", np.nan)) >= -1e-6,
            "PD_stressed_ge_baseline": row.get("PD_stressed_%", np.nan) >= row.get("PD_baseline_%", np.nan),
            "PD_lift_ge_floor": row.get("PD_final_lift", np.nan) >= row.get("PD_floor_lift", np.nan) - 1e-6,
        }
        rows.append({
            "Scenario": row.get("Scenario"),
            **checks,
            "validation_status": "OK" if all(checks.values()) else "REVIEW",
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 5. Migration de Stage sous stress (Matrice de Markov)
# ---------------------------------------------------------------------------
def compute_stage_migration(
    df: pd.DataFrame,
    df_stressed: pd.DataFrame,
    scenario_name: str,
) -> pd.DataFrame:
    """
    Estime la migration de stage sous stress.

    Méthode : les prêts dont la PD stressée dépasse des seuils de migration
    migrent de Stage 1 → 2 ou Stage 2 → 3.

    Seuils de migration (calibrés sur la pratique IFRS 9) :
    - Stage 1 → Stage 2 : PD_stressed / PD_baseline > 2.0 (doublement du risque)
    - Stage 2 → Stage 3 : PD_stressed > 0.30 (PD absolute > 30%)

    Returns : DataFrame avec 'stage_stressed' par prêt
    """
    result = df.copy()
    result["stage_stressed"] = result["stage"].copy()

    pd_base = df.get("PD_pred", pd.Series(0.05, index=df.index))
    pd_stress = df_stressed["PD_stressed"]

    # Stage 1 → Stage 2 : doublement de la PD
    cond_s1_to_s2 = (
        (result["stage"] == 1)
        & (pd_stress / pd_base.replace(0, 1e-6) > 2.0)
    )
    result.loc[cond_s1_to_s2, "stage_stressed"] = 2

    # Stage 2 → Stage 3 : PD absolue > 30%
    cond_s2_to_s3 = (result["stage"] == 2) & (pd_stress > 0.30)
    result.loc[cond_s2_to_s3, "stage_stressed"] = 3

    # Matrice de transition
    transition = pd.crosstab(
        result["stage"],
        result["stage_stressed"],
        normalize="index",
    ) * 100

    migration_stats = {
        "scenario":      scenario_name,
        "S1_to_S1_%":    round(transition.loc[1, 1] if (1, 1) in transition.stack().index else 100, 1),
        "S1_to_S2_%":    round(transition.loc[1, 2] if (1, 2) in transition.stack().index else 0, 1),
        "S2_to_S2_%":    round(transition.loc[2, 2] if (2, 2) in transition.stack().index else 100, 1),
        "S2_to_S3_%":    round(transition.loc[2, 3] if (2, 3) in transition.stack().index else 0, 1),
        "S3_maintained": 100.0,
        "n_migrated_S2": int(cond_s1_to_s2.sum()),
        "n_migrated_S3": int(cond_s2_to_s3.sum()),
    }

    print(f"\nMigration Stage [{scenario_name}] :")
    print(f"  Stage 1 → Stage 2 : {migration_stats['S1_to_S2_%']:.1f}% "
          f"({migration_stats['n_migrated_S2']:,} prêts)")
    print(f"  Stage 2 → Stage 3 : {migration_stats['S2_to_S3_%']:.1f}% "
          f"({migration_stats['n_migrated_S3']:,} prêts)")

    return result, migration_stats, transition


# ---------------------------------------------------------------------------
# 6. Pondération prospective IFRS 9
# ---------------------------------------------------------------------------
BASE_MARKOV_MATRIX = pd.DataFrame(
    [[0.925, 0.065, 0.010],
     [0.050, 0.760, 0.190],
     [0.000, 0.030, 0.970]],
    index=[1, 2, 3],
    columns=[1, 2, 3],
)


def stressed_markov_matrix(
    scenario: dict,
    base_matrix: pd.DataFrame = BASE_MARKOV_MATRIX,
) -> pd.DataFrame:
    """Construit une matrice de migration IFRS 9 stressee."""
    severity = macro_severity_score(scenario)
    matrix = base_matrix.copy().astype(float)

    matrix.loc[1, 2] += 0.10 * severity
    matrix.loc[1, 3] += 0.04 * severity
    matrix.loc[1, 1] = max(0.0, 1.0 - matrix.loc[1, 2] - matrix.loc[1, 3])

    matrix.loc[2, 3] += 0.22 * severity
    matrix.loc[2, 1] = max(0.0, matrix.loc[2, 1] * (1.0 - 0.75 * severity))
    matrix.loc[2, 2] = max(0.0, 1.0 - matrix.loc[2, 1] - matrix.loc[2, 3])

    matrix.loc[3, 3] = min(0.995, matrix.loc[3, 3] + 0.02 * severity)
    matrix.loc[3, 2] = 1.0 - matrix.loc[3, 3]
    matrix.loc[3, 1] = 0.0
    return matrix.clip(0.0, 1.0)


def compute_markov_stage_migration(
    df: pd.DataFrame,
    scenario: dict,
    scenario_name: str,
    base_matrix: pd.DataFrame = BASE_MARKOV_MATRIX,
) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    """
    Migration IFRS 9 par matrice de Markov stressee.

    Pour rester reproductible, les prets les plus risques absorbent en premier
    les migrations de degradation ciblees par la matrice.
    """
    matrix = stressed_markov_matrix(scenario, base_matrix)
    result = df.copy()
    result["stage_stressed"] = result["stage"].copy()
    risk_score = df.get("PD_stressed", df.get("PD_pred", pd.Series(0.0, index=df.index)))

    for initial_stage in [1, 2, 3]:
        idx = result.index[result["stage"] == initial_stage]
        if len(idx) == 0:
            continue
        probs = matrix.loc[initial_stage]
        ordered = risk_score.loc[idx].sort_values(ascending=False).index

        if initial_stage == 1:
            n_s3 = int(round(len(idx) * probs[3]))
            n_s2 = int(round(len(idx) * probs[2]))
            result.loc[ordered[:n_s3], "stage_stressed"] = 3
            result.loc[ordered[n_s3:n_s3 + n_s2], "stage_stressed"] = 2
        elif initial_stage == 2:
            n_s3 = int(round(len(idx) * probs[3]))
            n_s1 = int(round(len(idx) * probs[1]))
            result.loc[ordered[:n_s3], "stage_stressed"] = 3
            if n_s1 > 0:
                result.loc[ordered[-n_s1:], "stage_stressed"] = 1
        else:
            n_s2 = int(round(len(idx) * probs[2]))
            if n_s2 > 0:
                result.loc[ordered[-n_s2:], "stage_stressed"] = 2

    transition = pd.crosstab(
        result["stage"], result["stage_stressed"], normalize="index"
    ).reindex(index=[1, 2, 3], columns=[1, 2, 3], fill_value=0) * 100

    stats = {
        "scenario": scenario_name,
        "severity_score": round(macro_severity_score(scenario), 3),
        "S1_to_S2_%": round(float(transition.loc[1, 2]), 1),
        "S1_to_S3_%": round(float(transition.loc[1, 3]), 1),
        "S2_to_S3_%": round(float(transition.loc[2, 3]), 1),
        "S3_maintained_%": round(float(transition.loc[3, 3]), 1),
        "n_migrated": int((result["stage"] != result["stage_stressed"]).sum()),
    }
    return result, stats, transition


def compute_forward_looking_ecl(
    ecl_baseline: float,
    ecl_adverse: float,
    ecl_severe: float,
    weights: tuple[float, float, float] = (0.40, 0.35, 0.25),
) -> float:
    """
    ECL forward-looking IFRS 9 pondéré selon 3 scénarios.

    Poids par défaut (peut être calibré selon le jugement de la direction) :
    - 40% scénario base
    - 35% scénario adverse
    - 25% scénario sévère
    """
    w_base, w_adv, w_sev = weights
    ecl_fl = w_base * ecl_baseline + w_adv * ecl_adverse + w_sev * ecl_severe
    return ecl_fl


def compute_forward_looking_summary(
    ecl_baseline: float,
    stress_summary: pd.DataFrame,
    weights: dict | None = None,
    save: bool = True,
) -> pd.DataFrame:
    """
    Calcule une ECL IFRS 9 ponderee base/adverse/severe a partir du resume stress.
    """
    weights = weights or {"baseline": 0.40, "adverse": 0.35, "severe": 0.25}
    label_to_key = {v: k for k, v in SCENARIO_LABELS.items()}
    rows = [{"scenario_key": "baseline", "Scenario": "Baseline", "weight": weights.get("baseline", 0.0),
             "ECL_M$": ecl_baseline}]

    for _, row in stress_summary.iterrows():
        key = label_to_key.get(row["Scenario"], row["Scenario"])
        if key in weights:
            rows.append({
                "scenario_key": key,
                "Scenario": row["Scenario"],
                "weight": weights[key],
                "ECL_M$": row["ECL_stressed_M$"],
            })

    result = pd.DataFrame(rows)
    result["weighted_ECL_M$"] = result["weight"] * result["ECL_M$"]
    total = result["weighted_ECL_M$"].sum()
    result.loc[len(result)] = {
        "scenario_key": "forward_looking",
        "Scenario": "ECL Forward-Looking",
        "weight": result["weight"].sum(),
        "ECL_M$": total,
        "weighted_ECL_M$": total,
    }
    if save:
        result.to_csv(RESULTS_DIR / "forward_looking_ecl.csv", index=False)
    return result
