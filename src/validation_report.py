"""
validation_report.py - Rapport de validation modele/stress testing IFRS 9.

Ce module consolide les sorties CSV produites par les notebooks en un rapport
Markdown directement reutilisable dans le memoire ou la soutenance.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "outputs"
MODELS_DIR = OUTPUT_DIR / "models"
RESULTS_DIR = OUTPUT_DIR / "results"


def _read_csv(path: Path, **kwargs) -> pd.DataFrame:
    return pd.read_csv(path, **kwargs) if path.exists() else pd.DataFrame()


def _md_table(df: pd.DataFrame, max_rows: int = 12) -> str:
    if df.empty:
        return "_Non disponible. Executez les notebooks correspondants._"
    sample = df.head(max_rows).fillna("")
    cols = list(sample.columns)
    header = "| " + " | ".join(str(c) for c in cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    rows = []
    for _, row in sample.iterrows():
        values = [str(row[c]).replace("\n", " ") for c in cols]
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join([header, sep, *rows])


def generate_validation_report(
    output_path: str | Path = RESULTS_DIR / "validation_report.md",
) -> Path:
    """Genere un rapport Markdown de validation du stress testing."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pd_models = _read_csv(MODELS_DIR / "pd_model_comparison.csv")
    sat_models = _read_csv(MODELS_DIR / "satellite_pd_comparison.csv")
    wf = _read_csv(MODELS_DIR / "satellite_pd_walk_forward.csv")
    scenario_design = _read_csv(RESULTS_DIR / "scenario_design_validation.csv")
    stress_summary = _read_csv(RESULTS_DIR / "stress_ecl_summary.csv")
    stress_validation = _read_csv(RESULTS_DIR / "stress_validation_report.csv")
    forward = _read_csv(RESULTS_DIR / "forward_looking_ecl.csv")
    markov = _read_csv(RESULTS_DIR / "stage_migration_markov_summary.csv")
    cet1 = _read_csv(RESULTS_DIR / "cet1_resilience_table.csv")
    stress_models = _read_csv(RESULTS_DIR / "stress_model_comparison.csv")
    champion = _read_csv(RESULTS_DIR / "stress_model_champion.csv")
    fred_dict = _read_csv(RESULTS_DIR / "fred_variable_dictionary.csv")
    project_eval = _read_csv(RESULTS_DIR / "project_evaluation.csv")
    project_deductions = _read_csv(RESULTS_DIR / "project_evaluation_deductions.csv")
    final_audit = _read_csv(RESULTS_DIR / "final_banking_modeling_audit.csv")
    dfast_report = RESULTS_DIR / "dfast_like_report.md"

    wf_summary = pd.DataFrame()
    if not wf.empty and {"Model", "abs_error"}.issubset(wf.columns):
        wf_summary = wf.groupby("Model").agg(
            MAE=("abs_error", "mean"),
            RMSE=("abs_error", lambda x: float((x.pow(2).mean()) ** 0.5)),
            n_folds=("abs_error", "count"),
        ).reset_index().sort_values("RMSE")

    status = "OK"
    if not stress_validation.empty and "validation_status" in stress_validation.columns:
        status = "OK" if (stress_validation["validation_status"] == "OK").all() else "A revoir"

    lines = [
        "# Rapport de validation - Stress Testing IFRS 9",
        "",
        f"**Statut global des controles stress : {status}**",
        "",
        "## 1. Evaluation globale du projet",
        _md_table(project_eval),
        "",
        "### Penalites de maturite restantes",
        _md_table(project_deductions),
        "",
        "### Check-up final bancaire et modelisation",
        _md_table(final_audit, max_rows=30),
        "",
        "## 2. Modeles PD individuels",
        _md_table(pd_models),
        "",
        "## 3. Modeles satellites macro-PD",
        "Le champion doit etre performant statistiquement et coherent economiquement.",
        _md_table(sat_models),
        "",
        "## 4. Backtesting walk-forward satellite",
        _md_table(wf_summary),
        "",
        "## 5. Validation metier des scenarios",
        _md_table(scenario_design),
        "",
        "## 6. Utilisation des donnees FRED",
        _md_table(fred_dict),
        "",
        "## 7. Resultats de stress ECL",
        _md_table(stress_summary),
        "",
        "## 8. Controles automatiques de coherence",
        _md_table(stress_validation),
        "",
        "## 9. ECL forward-looking IFRS 9 (controle complementaire)",
        _md_table(forward),
        "",
        "## 10. Comparaison des moteurs de stress testing",
        (
            "Cette section compare des moteurs de stress concurrents: sensibilite "
            "deterministe, satellite macro, migration Markov, challenger ML et "
            "modele hybride. Le champion est retenu par scoring, pas par une "
            "ponderation forward-looking."
        ),
        _md_table(stress_models),
        "",
        "### Champion stress testing",
        _md_table(champion),
        "",
        "## 11. Migration IFRS 9 Markov",
        _md_table(markov),
        "",
        "## 12. Resilience CET1",
        _md_table(cet1),
        "",
        "## 13. Rapport DFAST-like",
        (
            f"Rapport disponible: `{dfast_report.relative_to(ROOT)}`"
            if dfast_report.exists()
            else "Rapport DFAST-like non encore genere."
        ),
        "",
        "## Conclusion de validation",
        (
            "Le moteur est valide pour un prototype academique si les controles de stress "
            "sont OK, si le satellite champion respecte la coherence economique et si les "
            "resultats CET1 restent interpretes comme une approximation pedagogique."
        ),
        "",
        "## Limites restantes",
        "- CET1 simplifie sauf integration d'un fichier FFIEC/capital reel.",
        "- Les scenarios COVID-2020 et choc marche 2018 sont des tests historiques calibres FRED.",
        "- Les resultats doivent etre figes apres execution sequentielle des notebooks.",
    ]
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


if __name__ == "__main__":
    print(generate_validation_report())
