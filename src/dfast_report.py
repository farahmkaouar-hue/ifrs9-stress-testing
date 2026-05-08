"""
dfast_report.py - Rapport DFAST-like pour le prototype IFRS 9 stress testing.

Le rapport reste academique: il reprend la structure d'un dossier prudentiel
sans pretendre remplacer un reporting reglementaire officiel.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.resilience import compute_cet1_impact


ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "outputs" / "results"
MODELS_DIR = ROOT / "outputs" / "models"


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def _md_table(df: pd.DataFrame, max_rows: int = 20) -> str:
    if df.empty:
        return "_Non disponible._"
    sample = df.head(max_rows).fillna("")
    cols = list(sample.columns)
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for _, row in sample.iterrows():
        values = [str(row[c]).replace("\n", " ") for c in cols]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def generate_dfast_report(
    output_path: str | Path = RESULTS_DIR / "dfast_like_report.md",
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    stress = _read_csv(RESULTS_DIR / "stress_ecl_summary.csv")
    cet1 = _read_csv(RESULTS_DIR / "cet1_resilience_table.csv")
    rst = _read_csv(RESULTS_DIR / "reverse_stress_test.csv")
    scenarios = _read_csv(RESULTS_DIR / "scenario_design_validation.csv")
    pd_models = _read_csv(MODELS_DIR / "pd_model_comparison.csv")
    final_audit = _read_csv(RESULTS_DIR / "final_banking_modeling_audit.csv")

    if not cet1.empty and "Shortfall_4_5_M$" not in cet1.columns:
        enriched_rows = []
        for _, row in cet1.iterrows():
            impact = compute_cet1_impact(
                ecl_baseline=float(row.get("ECL_baseline_M$", 0.0)),
                ecl_stressed=float(row.get("ECL_stressed_M$", 0.0)),
                ead_total=float(row.get("RWA_M$", 0.0)),
                cet1_initial=float(row.get("CET1_initial_%", 12.0)) / 100,
            )
            impact["Scenario"] = row.get("Scenario", "")
            enriched_rows.append(impact)
        cet1 = pd.DataFrame(enriched_rows)

    worst = None
    if not stress.empty and "ECL_lift" in stress.columns:
        worst = stress.sort_values("ECL_lift", ascending=False).iloc[0]

    critical_count = 0
    if not cet1.empty and "is_critical" in cet1.columns:
        critical_count = int(cet1["is_critical"].astype(str).str.lower().eq("true").sum())

    lines = [
        "# Rapport DFAST-like - Prototype IFRS 9 Stress Testing",
        "",
        "## 1. Resume executif",
        (
            "Ce rapport consolide les sorties du moteur IFRS 9 stress testing sous "
            "un format inspire des dossiers DFAST/CCAR: portefeuille, scenarios, "
            "methodologie, pertes, capital, reverse stress test et gouvernance modele."
        ),
        "",
        f"- Scenario le plus severe: {worst['Scenario']} (ECL lift {worst['ECL_lift']})" if worst is not None else "- Scenario le plus severe: non disponible.",
        f"- Scenarios critiques CET1: {critical_count}/{len(cet1)}" if not cet1.empty else "- Scenarios critiques CET1: non disponible.",
        "- Nature du rapport: prototype academique, non reporting reglementaire officiel.",
        "",
        "## 2. Portefeuille et donnees",
        (
            "Le portefeuille est derive de Lending Club. Les variables macroeconomiques "
            "proviennent de FRED. Le capital CET1/RWA reste parametre par hypotheses "
            "pedagogiques sauf integration ulterieure de donnees banque/FFIEC."
        ),
        "",
        "## 3. Scenarios macroeconomiques",
        _md_table(scenarios),
        "",
        "## 4. Methodologie modele",
        "- PD baseline: modeles de classification compares avec AUC, Gini, KS, Brier, PSI et LogLoss.",
        "- LGD/EAD: composantes construites en preprocessing puis stressees par sensibilites macro/taux.",
        "- Stress ECL: PD_stressed x LGD_stressed x EAD_stressed avec garde-fou ECL >= baseline.",
        "- Migration IFRS 9: matrice Markov stressee selon la severite macro.",
        "- Capital: impact des pertes nettes d'impot sur CET1 et shortfall aux seuils 4.5% et 7%.",
        "",
        "### Performance PD",
        _md_table(pd_models),
        "",
        "## 5. Resultats pertes sous stress",
        _md_table(stress),
        "",
        "## 6. Capital, shortfall et actions managériales",
        _md_table(cet1),
        "",
        "## 7. Reverse stress test",
        _md_table(rst),
        "",
        "## 8. Gouvernance et limites",
        _md_table(final_audit),
        "",
        "## 9. Conclusion prudentielle",
        (
            "Le prototype permet d'identifier les scenarios les plus penal en ECL, "
            "les zones de rupture CET1 et les reserves methodologiques. Pour une "
            "utilisation bancaire reelle, il faut ajouter donnees internes, capital "
            "reel, validation externe independante, monitoring et revue modele."
        ),
    ]
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


if __name__ == "__main__":
    print(generate_dfast_report())
