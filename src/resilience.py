"""
resilience.py — Analyse de résilience bancaire : impact sur CET1,
courbe de résilience et Reverse Stress Test.

Usage:
    from src.resilience import compute_cet1_impact, resilience_curve, reverse_stress_test
"""

import numpy as np
import pandas as pd
import joblib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "outputs" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_DIR = ROOT / "config"

# ---------------------------------------------------------------------------
# Constantes réglementaires
# ---------------------------------------------------------------------------
CET1_INITIAL          = 0.12    # 12% — hypothèse simplifiée (US 2007-2018)
CET1_REGULATORY_MIN   = 0.045   # 4.5% — seuil Bâle III
CET1_CONSERVATION     = 0.025   # 2.5% — coussin de conservation
CET1_TOTAL_MIN        = CET1_REGULATORY_MIN + CET1_CONSERVATION  # 7%


def load_capital_assumptions(path: str | Path | None = None) -> dict:
    """
    Charge les hypotheses capital/RWA depuis config/capital_assumptions.csv.

    Format attendu :
        parameter,value
        cet1_initial_pct,12.0
        tax_rate_pct,30.0
        rwa_multiplier,1.0

    Le projet reste compatible avec l'hypothese simplifiee si le fichier manque.
    """
    path = Path(path) if path else CONFIG_DIR / "capital_assumptions.csv"
    defaults = {
        "cet1_initial_pct": CET1_INITIAL * 100,
        "tax_rate_pct": 30.0,
        "rwa_multiplier": 1.0,
    }
    if not path.exists():
        return defaults
    df = pd.read_csv(path)
    if {"parameter", "value"}.issubset(df.columns):
        loaded = dict(zip(df["parameter"], df["value"]))
        defaults.update({k: float(v) for k, v in loaded.items() if k in defaults})
    return defaults


def compute_cet1_impact_advanced(
    ecl_baseline: float,
    ecl_stressed: float,
    ead_total: float,
    assumptions: dict | None = None,
) -> dict:
    """
    Version parametree du calcul CET1.

    ecl_baseline/ecl_stressed/ead_total sont en M$.
    RWA = EAD x rwa_multiplier.
    Capital CET1 initial = CET1_initial x RWA.
    """
    assumptions = assumptions or load_capital_assumptions()
    cet1_initial = assumptions.get("cet1_initial_pct", CET1_INITIAL * 100) / 100
    tax_rate = assumptions.get("tax_rate_pct", 30.0) / 100
    rwa = ead_total * assumptions.get("rwa_multiplier", 1.0)
    return compute_cet1_impact(
        ecl_baseline=ecl_baseline,
        ecl_stressed=ecl_stressed,
        ead_total=rwa,
        cet1_initial=cet1_initial,
        tax_rate=tax_rate,
    )


# ---------------------------------------------------------------------------
# 1. Calcul de l'impact du stress sur le CET1
# ---------------------------------------------------------------------------
def compute_cet1_impact(
    ecl_baseline: float,
    ecl_stressed: float,
    ead_total: float,
    cet1_initial: float = CET1_INITIAL,
    tax_rate: float = 0.30,
) -> dict:
    """
    Calcule l'impact du stress sur le ratio CET1.

    ΔECL = ECL_stressed - ECL_baseline
    ΔCET1 (en montant) = -ΔECL × (1 - tax_rate)  [charge d'impôt réduit la perte nette]
    ΔCET1 (en ratio)   = ΔCET1_montant / RWA
    RWA simplifié      = EAD_total (risk weight 100%)

    Parameters
    ----------
    ecl_baseline : float (M$)
    ecl_stressed : float (M$)
    ead_total    : float (M$)
    cet1_initial : float (ratio, ex: 0.12)
    tax_rate     : float (taux d'impôt normalisé ~30%)

    Returns
    -------
    dict avec CET1_initial, ΔCET1, CET1_post_stress, zone (OK/Attention/Critique/Rupture)
    """
    delta_ecl = ecl_stressed - ecl_baseline       # en M$
    delta_ecl_net = delta_ecl * (1 - tax_rate)    # impact net d'impôt (M$)
    rwa = ead_total                                # RWA simplifié

    delta_cet1_ratio = -(delta_ecl_net / rwa) if rwa > 0 else 0.0
    cet1_post = cet1_initial + delta_cet1_ratio

    # Classification réglementaire
    if cet1_post >= CET1_TOTAL_MIN:
        zone = "✓ Résilient (CET1 ≥ 7%)"
        color = "green"
        management_action = "Surveillance normale et maintien des coussins."
    elif cet1_post >= CET1_REGULATORY_MIN:
        zone = "⚠ Attention (4.5% ≤ CET1 < 7%)"
        color = "orange"
        management_action = "Plan de conservation capital: limiter dividendes, reduire croissance RWA, renforcer recouvrement."
    elif cet1_post > 0:
        zone = "🚨 Critique (CET1 < 4.5% — Bâle III)"
        color = "red"
        management_action = "Plan de recapitalisation: injection capital, cession actifs risques, reduction origination."
    else:
        zone = "💥 Rupture (CET1 < 0% — Défaillance)"
        color = "darkred"
        management_action = "Resolution/restructuration: recapitalisation urgente ou plan de resolution."

    capital_initial = cet1_initial * rwa
    capital_post = cet1_post * rwa
    required_capital_45 = CET1_REGULATORY_MIN * rwa
    required_capital_70 = CET1_TOTAL_MIN * rwa
    shortfall_45 = max(required_capital_45 - capital_post, 0.0)
    shortfall_70 = max(required_capital_70 - capital_post, 0.0)

    return {
        "CET1_initial_%":       round(cet1_initial * 100, 2),
        "ECL_baseline_M$":      round(ecl_baseline, 2),
        "ECL_stressed_M$":      round(ecl_stressed, 2),
        "ΔECL_M$":              round(delta_ecl, 2),
        "ΔECL_net_M$":          round(delta_ecl_net, 2),
        "ΔCET1_%":              round(delta_cet1_ratio * 100, 2),
        "CET1_post_stress_%":   round(cet1_post * 100, 2),
        "RWA_M$":               round(rwa, 2),
        "Capital_initial_M$":    round(capital_initial, 2),
        "Capital_post_M$":       round(capital_post, 2),
        "Shortfall_4_5_M$":      round(shortfall_45, 2),
        "Shortfall_7_0_M$":      round(shortfall_70, 2),
        "zone":                 zone,
        "color":                color,
        "management_action":     management_action,
        "is_critical":          cet1_post < CET1_REGULATORY_MIN,
    }


# ---------------------------------------------------------------------------
# 2. Tableau de bord CET1 multi-scénarios
# ---------------------------------------------------------------------------
def compute_cet1_table(
    ecl_baseline: float,
    stressed_results: dict,
    ead_total: float,
    cet1_initial: float = CET1_INITIAL,
) -> pd.DataFrame:
    """
    Génère le tableau de bord CET1 pour tous les scénarios de stress.

    Parameters
    ----------
    stressed_results : dict {scenario_name: df_stressed}
        Retourné par stress_scenarios.compute_stress_ecl()
    """
    from src.stress_scenarios import SCENARIO_LABELS

    rows = []
    for name, df_stressed in stressed_results.items():
        ecl_s = df_stressed["ECL_stressed"].sum() / 1e6
        impact = compute_cet1_impact(ecl_baseline, ecl_s, ead_total / 1e6, cet1_initial)
        impact["Scenario"] = SCENARIO_LABELS.get(name, name)
        rows.append(impact)

    df_table = pd.DataFrame(rows).set_index("Scenario")
    df_table.to_csv(RESULTS_DIR / "cet1_resilience_table.csv")
    print(f"Table CET1 sauvegardée : {RESULTS_DIR / 'cet1_resilience_table.csv'}")
    return df_table


# ---------------------------------------------------------------------------
# 3. Courbe de résilience
# ---------------------------------------------------------------------------
def resilience_curve(
    df: pd.DataFrame,
    ecl_baseline: float,
    champion_pd_model,
    features: list[str],
    satellite_pd_model: dict,
    satellite_pd_features: list[str],
    satellite_pd_champion: str = "OLS",
    n_points: int = 30,
    max_intensity: float = 2.5,
    cet1_initial: float = CET1_INITIAL,
    tax_rate: float = 0.30,
) -> pd.DataFrame:
    """
    Calcule la courbe CET1 en fonction de l'intensité du choc.

    L'intensité varie de 0 (baseline) à max_intensity × scénario sévère.
    Chaque point = interpolation linéaire entre baseline et scénario 2008.

    Returns : DataFrame avec colonnes intensity, CET1, ECL_stressed
    """
    from src.stress_scenarios import SCENARIOS, apply_stress

    base_scenario = SCENARIOS["baseline"]
    severe_scenario = SCENARIOS["crisis_2008"]

    intensities = np.linspace(0, max_intensity, n_points)
    curve_data = []

    ead_total = df["EAD"].sum()

    print("Calcul de la courbe de résilience...")
    for intensity in intensities:
        # Interpolation linéaire entre baseline et scénario sévère
        scenario_i = {
            k: base_scenario[k] + intensity * (severe_scenario[k] - base_scenario[k])
            for k in base_scenario
        }

        try:
            df_s = apply_stress(
                df, scenario_i, f"intensity_{intensity:.2f}",
                champion_pd_model, features,
                satellite_pd_model, satellite_pd_features, satellite_pd_champion,
            )
            ecl_s = df_s["ECL_stressed"].sum() / 1e6
        except Exception:
            ecl_s = ecl_baseline

        impact = compute_cet1_impact(
            ecl_baseline, ecl_s, ead_total / 1e6, cet1_initial, tax_rate
        )

        curve_data.append({
            "intensity":            round(intensity, 3),
            "scenario_unrate_%":    round(scenario_i["UNRATE"], 2),
            "scenario_gdp_%":       round(scenario_i["GDPC1_growth"], 2),
            "scenario_fedfunds_%":  round(scenario_i["FEDFUNDS"], 2),
            "ECL_stressed_M$":      round(ecl_s, 2),
            "ΔECL_M$":              round(ecl_s - ecl_baseline, 2),
            "CET1_%":               round(impact["CET1_post_stress_%"], 3),
            "ΔCET1_%":              round(impact["ΔCET1_%"], 3),
            "is_critical":          impact["is_critical"],
        })

    curve_df = pd.DataFrame(curve_data)
    curve_df.to_csv(RESULTS_DIR / "resilience_curve.csv", index=False)
    print(f"Courbe de résilience sauvegardée ({n_points} points) : "
          f"{RESULTS_DIR / 'resilience_curve.csv'}")

    return curve_df


# ---------------------------------------------------------------------------
# 4. Reverse Stress Test — Binary Search
# ---------------------------------------------------------------------------
def reverse_stress_test(
    df: pd.DataFrame,
    ecl_baseline: float,
    champion_pd_model,
    features: list[str],
    satellite_pd_model: dict,
    satellite_pd_features: list[str],
    satellite_pd_champion: str = "OLS",
    target_cet1: float = CET1_REGULATORY_MIN,
    cet1_initial: float = CET1_INITIAL,
    tolerance: float = 0.001,
    max_iter: int = 50,
) -> dict:
    """
    Trouve le choc minimum (intensité) qui amène le CET1 au seuil cible.

    Algorithme : recherche binaire (bisection) sur l'intensité du choc.
    - Plage : [0, 3.0] × scénario 2008
    - Convergence quand |CET1_post - target| < tolerance

    Returns : dict avec intensité critique, valeurs macro critiques, CET1 atteint
    """
    from src.stress_scenarios import SCENARIOS, apply_stress

    base_scenario = SCENARIOS["baseline"]
    severe_scenario = SCENARIOS["crisis_2008"]
    ead_total = df["EAD"].sum() / 1e6

    def evaluate_cet1(intensity):
        scenario_i = {
            k: base_scenario[k] + intensity * (severe_scenario[k] - base_scenario[k])
            for k in base_scenario
        }
        try:
            df_s = apply_stress(
                df, scenario_i, "rst",
                champion_pd_model, features,
                satellite_pd_model, satellite_pd_features, satellite_pd_champion,
            )
            ecl_s = df_s["ECL_stressed"].sum() / 1e6
        except Exception:
            ecl_s = ecl_baseline

        impact = compute_cet1_impact(ecl_baseline, ecl_s, ead_total, cet1_initial)
        return impact["CET1_post_stress_%"] / 100, ecl_s

    print(f"\n=== Reverse Stress Test ===")
    print(f"Recherche de l'intensité qui amène CET1 → {target_cet1:.1%}...")

    # Vérification que le scénario le plus sévère dépasse le seuil
    cet1_at_max, _ = evaluate_cet1(3.0)
    if cet1_at_max > target_cet1:
        print("⚠ Même à 3× le scénario 2008, le CET1 reste > seuil. Banque très résiliente.")
        return {
            "intensity_critical":   None,
            "cet1_achieved_%":      round(cet1_at_max * 100, 2),
            "target_cet1_%":        round(target_cet1 * 100, 2),
            "message":              "Le portefeuille est très résilient — seuil non atteint à 3× la crise 2008"
        }

    # Recherche binaire
    low, high = 0.0, 3.0
    intensity_critical = None
    ecl_critical = ecl_baseline

    for _ in range(max_iter):
        mid = (low + high) / 2
        cet1_mid, ecl_mid = evaluate_cet1(mid)

        if abs(cet1_mid - target_cet1) < tolerance:
            intensity_critical = mid
            ecl_critical = ecl_mid
            break

        if cet1_mid > target_cet1:
            low = mid
        else:
            high = mid

    if intensity_critical is None:
        intensity_critical = (low + high) / 2

    # Valeurs macro au point de rupture
    macro_critical = {
        k: round(base_scenario[k] + intensity_critical * (severe_scenario[k] - base_scenario[k]), 2)
        for k in base_scenario
    }

    cet1_final, _ = evaluate_cet1(intensity_critical)

    result = {
        "intensity_critical":   round(intensity_critical, 3),
        "cet1_achieved_%":      round(cet1_final * 100, 2),
        "target_cet1_%":        round(target_cet1 * 100, 2),
        "ECL_critical_M$":      round(ecl_critical, 2),
        "ECL_baseline_M$":      round(ecl_baseline, 2),
        "ECL_lift":             round(ecl_critical / max(ecl_baseline, 1e-6), 2),
        "macro_critical":       macro_critical,
    }

    print(f"\n✓ Point de rupture trouvé à intensité × {intensity_critical:.3f}")
    print(f"   CET1 atteint          : {cet1_final:.2%}")
    print(f"   UNRATE critique       : {macro_critical['UNRATE']:.1f}%")
    print(f"   PIB growth critique   : {macro_critical['GDPC1_growth']:.1f}%")
    print(f"   Fed Funds critique    : {macro_critical['FEDFUNDS']:.1f}%")
    print(f"   ECL critique          : ${ecl_critical:,.1f} M (×{ecl_critical/max(ecl_baseline,1e-6):.2f})")

    # Sauvegarde
    pd.DataFrame([result]).to_csv(RESULTS_DIR / "reverse_stress_test.csv", index=False)

    return result


# ---------------------------------------------------------------------------
# 5. Résumé de résilience complet
# ---------------------------------------------------------------------------
def generate_resilience_report(
    ecl_baseline: float,
    cet1_table: pd.DataFrame,
    curve_df: pd.DataFrame,
    rst_result: dict,
) -> pd.DataFrame:
    """Génère un rapport de résilience formaté."""
    print("\n" + "=" * 60)
    print("RAPPORT DE RÉSILIENCE BANCAIRE — IFRS 9 STRESS TESTING")
    print("=" * 60)
    print(f"\nCET1 initial         : {CET1_INITIAL:.1%}")
    print(f"Seuil réglementaire  : {CET1_REGULATORY_MIN:.1%} (Bâle III)")
    print(f"ECL baseline         : ${ecl_baseline:,.1f} M")

    print("\n--- Impact par Scénario ---")
    display_cols = ["CET1_post_stress_%", "ΔCET1_%", "ΔECL_M$", "ECL_lift", "zone"]
    available = [c for c in display_cols if c in cet1_table.columns]
    print(cet1_table[available].to_string())

    if rst_result.get("intensity_critical") is not None:
        print(f"\n--- Reverse Stress Test ---")
        print(f"Point de rupture CET1 = {rst_result['target_cet1_%']:.1f}% "
              f"atteint pour :")
        for k, v in rst_result["macro_critical"].items():
            print(f"  {k:20s} : {v}")

    # Courbe : premier point critique
    crit_pts = curve_df[curve_df["is_critical"]]
    if len(crit_pts) > 0:
        first_crit = crit_pts.iloc[0]
        print(f"\n  Première intensité critique (CET1 < 4.5%) : ×{first_crit['intensity']:.2f}")
        print(f"  UNRATE correspondant  : {first_crit['scenario_unrate_%']:.1f}%")

    print("=" * 60)
    return cet1_table
