"""
run_final_pipeline.py - Pipeline final post-notebooks.

Execute les scripts finaux dans le bon ordre apres le notebook 07:
1. comparaison des moteurs de stress,
2. evaluation globale du projet,
3. check-up bancaire/modelisation,
4. rapport de validation consolide,
5. alignement des notebooks 01-07,
6. revue bancaire experte,
7. tests metier rapides.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.evaluate_project import generate_project_evaluation
from scripts.align_notebooks_banking_story import align_all_notebooks
from scripts.final_banking_audit import run_final_banking_audit
from scripts.generate_banking_expert_review import generate_banking_expert_outputs
from scripts.run_business_tests import TESTS
from src.dfast_report import generate_dfast_report
from src.stress_scenarios import validate_scenario_design
from src.stress_model_comparison import compare_stress_testing_models
from src.validation_report import generate_validation_report


def _existing_result(name: str, *relative_paths: str) -> tuple[Path, ...]:
    paths = tuple(ROOT / rel for rel in relative_paths)
    if all(path.exists() for path in paths):
        print(f"[WARN] {name}: fichier verrouille, utilisation des sorties existantes.")
        return paths
    raise PermissionError(
        f"{name}: un fichier de sortie est verrouille et aucune sortie existante "
        "complete n'est disponible. Fermez Excel/Streamlit puis relancez."
    )


def compare_stress_models_step() -> str:
    path = ROOT / "outputs" / "ecl_baseline.parquet"
    if not path.exists():
        path = ROOT / "outputs" / "loan_clean.parquet"
    if not path.exists():
        raise FileNotFoundError("Executez d'abord les notebooks 02 et 03.")
    df = pd.read_parquet(path)
    try:
        _, champion = compare_stress_testing_models(df)
        return champion
    except PermissionError:
        champion_path = ROOT / "outputs" / "results" / "stress_model_champion.csv"
        if champion_path.exists():
            champion_df = pd.read_csv(champion_path)
            if not champion_df.empty and "champion_model" in champion_df.columns:
                return str(champion_df.loc[0, "champion_model"])
        raise PermissionError(
            "Impossible d'ecrire stress_model_comparison.csv. Fermez le fichier "
            "dans Excel/Streamlit ou relancez le notebook apres fermeture."
        )


def run_business_tests_step() -> int:
    passed = 0
    for test in TESTS:
        try:
            test()
            passed += 1
        except PermissionError as exc:
            print(f"[WARN] Test {test.__name__} non execute car un fichier est verrouille: {exc}")
    return passed


def run_final_pipeline(run_tests: bool = True) -> dict:
    champion = compare_stress_models_step()
    try:
        validate_scenario_design()
    except PermissionError:
        _existing_result("Validation scenarios", "outputs/results/scenario_design_validation.csv")
    try:
        project_md, project_csv = generate_project_evaluation()
    except PermissionError:
        project_md, project_csv = _existing_result(
            "Evaluation projet",
            "outputs/results/project_evaluation.md",
            "outputs/results/project_evaluation.csv",
        )
    try:
        audit_md, audit_csv = run_final_banking_audit()
    except PermissionError:
        audit_md, audit_csv = _existing_result(
            "Audit final",
            "outputs/results/final_banking_modeling_audit.md",
            "outputs/results/final_banking_modeling_audit.csv",
        )
    try:
        validation_md = generate_validation_report()
    except PermissionError:
        (validation_md,) = _existing_result(
            "Rapport validation",
            "outputs/results/validation_report.md",
        )
    try:
        dfast_md = generate_dfast_report()
    except PermissionError:
        (dfast_md,) = _existing_result(
            "Rapport DFAST-like",
            "outputs/results/dfast_like_report.md",
        )
    try:
        aligned_notebooks = [str(path) for path in align_all_notebooks()]
    except PermissionError:
        aligned_notebooks = ["notebooks_locked"]
    try:
        expert_outputs = generate_banking_expert_outputs()
    except PermissionError:
        _existing_result(
            "Revue bancaire experte",
            "notebooks/08_Banking_Expert_Review.ipynb",
            "outputs/results/one_year_stress_decision_matrix.csv",
            "outputs/results/basel_capital_metrics.csv",
        )
        expert_outputs = {"status": "existing_outputs"}
    n_tests = run_business_tests_step() if run_tests else 0
    try:
        validate_scenario_design()
        dfast_md = generate_dfast_report()
        validation_md = generate_validation_report()
    except PermissionError:
        pass
    return {
        "stress_champion": champion,
        "project_evaluation_md": str(project_md),
        "project_evaluation_csv": str(project_csv),
        "final_audit_md": str(audit_md),
        "final_audit_csv": str(audit_csv),
        "validation_report_md": str(validation_md),
        "dfast_like_report_md": str(dfast_md),
        "aligned_notebooks": aligned_notebooks,
        "banking_expert_outputs": expert_outputs,
        "business_tests_passed": n_tests,
    }


if __name__ == "__main__":
    result = run_final_pipeline(run_tests=True)
    for key, value in result.items():
        print(f"{key}: {value}")
