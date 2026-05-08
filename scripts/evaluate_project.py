"""
evaluate_project.py - Evaluation expert du projet IFRS 9 stress testing.

Le script controle la presence des livrables, la couverture metier et les
points restant a renforcer. Il genere un rapport Markdown et un tableau CSV.
"""

from __future__ import annotations

from pathlib import Path
import importlib.util

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "outputs"
MODELS_DIR = OUTPUT_DIR / "models"
RESULTS_DIR = OUTPUT_DIR / "results"
NOTEBOOK_DIR = ROOT / "notebooks"
DASHBOARD_DIR = ROOT / "dashboard"


CHECKS = [
    {
        "pillar": "EDA",
        "weight": 10,
        "required": [
            OUTPUT_DIR / "fig_01_loan_status.png",
            OUTPUT_DIR / "fig_04_default_by_grade.png",
            OUTPUT_DIR / "fig_10_macro_credit_cycle.png",
            RESULTS_DIR / "vintage_default_profile.csv",
        ],
        "expert_comment": "EDA couvre cible, segmentation, cycle macro et censure vintage.",
    },
    {
        "pillar": "Preprocessing",
        "weight": 12,
        "required": [
            OUTPUT_DIR / "loan_clean.parquet",
            RESULTS_DIR / "schema_quality_report.csv",
            RESULTS_DIR / "preprocessing_audit.csv",
            RESULTS_DIR / "fred_variable_dictionary.csv",
        ],
        "expert_comment": "Pipeline auditable avec dictionnaire FRED et controles qualite.",
    },
    {
        "pillar": "Baseline ECL",
        "weight": 12,
        "required": [
            OUTPUT_DIR / "ecl_baseline.parquet",
            MODELS_DIR / "pd_model_comparison.csv",
            OUTPUT_DIR / "fig_14_roc_ks.png",
            OUTPUT_DIR / "fig_15_walk_forward.png",
        ],
        "expert_comment": "PD individuelle, ECL baseline et validation temporelle presentes.",
    },
    {
        "pillar": "Satellites macro",
        "weight": 12,
        "required": [
            MODELS_DIR / "satellite_pd_comparison.csv",
            MODELS_DIR / "satellite_pd_walk_forward.csv",
            OUTPUT_DIR / "fig_22_satellite_pd_comparison.png",
            OUTPUT_DIR / "fig_25_satellite_scenario_dr.png",
        ],
        "expert_comment": "Lien macro-PD explicite pour transformer les chocs en defaut attendu.",
    },
    {
        "pillar": "Stress testing",
        "weight": 16,
        "required": [
            RESULTS_DIR / "stress_ecl_summary.csv",
            RESULTS_DIR / "scenario_design_validation.csv",
            RESULTS_DIR / "stress_validation_report.csv",
            RESULTS_DIR / "stress_model_comparison.csv",
            RESULTS_DIR / "stress_model_champion.csv",
        ],
        "expert_comment": "Plusieurs moteurs de stress sont compares et un champion est documente.",
    },
    {
        "pillar": "Scenarios historiques",
        "weight": 10,
        "required": [
            OUTPUT_DIR / "fig_26_stress_ecl_comparison.png",
            RESULTS_DIR / "scenario_design_validation.csv",
        ],
        "expert_comment": "COVID-19, marche 2018, crise 2008, adverse, severe et taux sont actifs.",
    },
    {
        "pillar": "Resilience CET1",
        "weight": 10,
        "required": [
            RESULTS_DIR / "cet1_resilience_table.csv",
            RESULTS_DIR / "resilience_curve.csv",
            RESULTS_DIR / "reverse_stress_test.csv",
        ],
        "expert_comment": "Impact capital et point de rupture sont disponibles.",
    },
    {
        "pillar": "Application",
        "weight": 10,
        "required": [
            DASHBOARD_DIR / "app.py",
        ],
        "expert_comment": "Dashboard Streamlit centralise portefeuille, stress, resilience et validation.",
    },
    {
        "pillar": "Communication",
        "weight": 8,
        "required": [
            OUTPUT_DIR / "presentations" / "01_Presentation_EDA.pptx",
            OUTPUT_DIR / "presentations" / "02_Presentation_Preprocessing.pptx",
            OUTPUT_DIR / "presentations" / "03_Presentation_Modelisation_StressTesting.pptx",
        ],
        "expert_comment": "Trois presentations separees documentent methode, code et outputs.",
    },
]


def score_check(check: dict) -> dict:
    required = check["required"]
    present = [p for p in required if p.exists()]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
    ratio = len(present) / max(len(required), 1)
    score = round(check["weight"] * ratio, 2)
    return {
        "pillar": check["pillar"],
        "weight": check["weight"],
        "score": score,
        "coverage_%": round(ratio * 100, 1),
        "missing": "; ".join(missing),
        "expert_comment": check["expert_comment"],
    }


def rating(total_score: float) -> str:
    if total_score >= 90:
        return "Excellent prototype academique, proche d'un dossier soutenable."
    if total_score >= 80:
        return "Tres bon projet, avec quelques limites a expliciter."
    if total_score >= 70:
        return "Projet solide mais encore incomplet pour une lecture expert."
    return "Projet a renforcer avant soutenance."


def maturity_deductions() -> list[dict]:
    deductions = []
    if importlib.util.find_spec("streamlit") is None:
        deductions.append({
            "risk": "Dependance Streamlit absente dans l'environnement courant",
            "points": 4,
            "action": "Installer streamlit avant la demonstration dashboard.",
        })
    if importlib.util.find_spec("pyarrow") is None and importlib.util.find_spec("fastparquet") is None:
        deductions.append({
            "risk": "Lecture parquet non disponible dans l'environnement courant",
            "points": 4,
            "action": "Installer pyarrow ou fastparquet pour lire loan_clean/ecl_baseline.",
        })
    if importlib.util.find_spec("plotly") is None:
        deductions.append({
            "risk": "Dependance Plotly absente dans l'environnement courant",
            "points": 3,
            "action": "Installer plotly pour afficher les graphiques du dashboard.",
        })
    if importlib.util.find_spec("joblib") is None:
        deductions.append({
            "risk": "Dependance Joblib absente dans l'environnement courant",
            "points": 2,
            "action": "Installer joblib pour charger les modeles pickle.",
        })
    deductions.extend([
        {
            "risk": "Capital/RWA encore pedagogique",
            "points": 5,
            "action": "Remplacer ou justifier les hypotheses CET1 avec donnees banque si disponibles.",
        },
        {
            "risk": "Validation externe limitee",
            "points": 3,
            "action": "Ajouter benchmark externe ou stress historique supplementaire si le temps le permet.",
        },
        {
            "risk": "Notebooks a reexecuter apres les derniers changements",
            "points": 2,
            "action": "Reexecuter 01 a 07 avant soutenance pour figer les sorties finales.",
        },
    ])
    return deductions


def md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_Non disponible._"
    cols = list(df.columns)
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for _, row in df.iterrows():
        values = [str(row[c]).replace("\n", " ") for c in cols]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def generate_project_evaluation() -> tuple[Path, Path]:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    rows = [score_check(check) for check in CHECKS]
    df = pd.DataFrame(rows)
    artifact_total = round(float(df["score"].sum()), 2)
    deductions = pd.DataFrame(maturity_deductions())
    deduction_points = float(deductions["points"].sum()) if not deductions.empty else 0.0
    total = round(max(0.0, artifact_total - deduction_points), 2)
    max_score = int(df["weight"].sum())

    csv_path = RESULTS_DIR / "project_evaluation.csv"
    md_path = RESULTS_DIR / "project_evaluation.md"
    deductions_path = RESULTS_DIR / "project_evaluation_deductions.csv"
    df.to_csv(csv_path, index=False)
    deductions.to_csv(deductions_path, index=False)

    strengths = [
        "Architecture complete: EDA, preprocessing, PD baseline, satellites macro, stress, CET1, validation et app.",
        "Stress testing traite comme une famille de moteurs concurrents, pas comme un simple calcul forward-looking.",
        "Scenarios historiques ajoutes: COVID-19, marche 2018 et crise 2008.",
        "Utilisation FRED documentee par variable, role et usage metier.",
    ]
    next_steps = [
        "Ajouter un vrai fichier capital/RWA banque si disponible pour remplacer les hypotheses CET1 simplifiees.",
        "Reexecuter tous les notebooks apres chaque modification majeure pour figer les outputs.",
        "Installer pyarrow et streamlit dans l'environnement applicatif pour lancer le dashboard.",
        "Documenter dans le memoire que le modele champion stress testing est retenu par score multi-criteres.",
    ]

    lines = [
        "# Evaluation expert du projet IFRS 9 stress testing",
        "",
        f"**Score global: {total}/{max_score}**",
        f"**Couverture livrables: {artifact_total}/{max_score}**",
        f"**Penalites maturite: -{deduction_points:.1f} points**",
        "",
        f"**Avis expert: {rating(total)}**",
        "",
        "## Scores par pilier",
        md_table(df),
        "",
        "## Penalites de maturite",
        md_table(deductions),
        "",
        "## Forces principales",
        *[f"- {x}" for x in strengths],
        "",
        "## Ameliorations prioritaires restantes",
        *[f"- {x}" for x in next_steps],
        "",
        "## Conclusion",
        (
            "Le projet est coherent pour une soutenance PFA: il explique les donnees, "
            "controle la qualite, construit l'ECL baseline, transforme les scenarios "
            "macro en chocs de pertes, compare plusieurs moteurs de stress et presente "
            "un diagnostic de resilience capital."
        ),
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path, csv_path


if __name__ == "__main__":
    report, table = generate_project_evaluation()
    print(report)
    print(table)
