"""
generate_banking_expert_review.py - Notebook et sorties expert bancaire.

Ce script cree un notebook 08 audit-friendly et regenere les sorties clefs:
- capital/RWA Bale,
- segmentation reglementaire,
- matrice stress testing 1 an,
- projection dynamique T1-T5,
- registre modele et audit trail.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

NOTEBOOK_PATH = ROOT / "notebooks" / "08_Banking_Expert_Review.ipynb"
OUTPUT_DIR = ROOT / "outputs"
RESULTS_DIR = ROOT / "outputs" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


BANKING_INPUT_COLS = [
    "issue_d",
    "purpose",
    "grade",
    "stage",
    "loan_amnt",
    "EAD",
    "LGD",
    "term_months",
]


def markdown_cell(source: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": source.strip().splitlines(True),
    }


def code_cell(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.strip().splitlines(True),
    }


def build_notebook() -> dict:
    cells = [
        markdown_cell(
            """
            # 08 - Revue bancaire experte: IFRS 9, Bale et stress testing

            Ce notebook complete les notebooks 01 a 07 avec une vue de plateforme bancaire:
            date d'arrete, segmentation reglementaire, RWA, capital stack, stress testing a 1 an,
            projection T1-T5, gouvernance modele et audit trail.

            Objectif de soutenance: montrer que le projet ne calcule pas seulement une ECL totale,
            mais simule une decision bancaire: perte attendue l'annee prochaine, resistance capital
            et actions de management.
            """
        ),
        code_cell(
            """
            import sys
            from pathlib import Path

            import pandas as pd

            ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
            sys.path.insert(0, str(ROOT))

            from src.banking_core import (
                capital_actions_from_shortfall,
                compute_basel_metrics,
                enrich_banking_view,
                ensure_model_registry,
                load_audit_log,
                log_audit_event,
                segment_summary,
            )
            from src.scenario_projection import compute_dynamic_projection
            from src.stress_scenarios import ACTIVE_STRESS_SCENARIOS, SCENARIO_LABELS

            OUTPUT_DIR = ROOT / "outputs"
            RESULTS_DIR = OUTPUT_DIR / "results"
            RESULTS_DIR.mkdir(parents=True, exist_ok=True)
            """
        ),
        markdown_cell(
            """
            ## 1. Portefeuille a date d'arrete

            Une banque ne travaille pas sur tout l'historique brut. Elle fige un portefeuille a une
            date de reporting, puis calcule ECL, RWA et stress testing sur cette photographie.
            """
        ),
        code_cell(
            """
            df_full = pd.read_parquet(OUTPUT_DIR / "loan_clean.parquet")
            ecl = pd.read_parquet(OUTPUT_DIR / "ecl_baseline.parquet")
            cols = [c for c in ["issue_d", "purpose", "grade", "stage", "loan_amnt", "EAD", "LGD", "term_months"] if c in df_full.columns]
            df = df_full[cols].copy()
            df["PD_pred"] = ecl["PD_pred"].values
            df["ECL_ifrs9"] = ecl["ECL_ifrs9"].values
            del df_full, ecl

            reporting_date = pd.to_datetime(df["issue_d"]).max() if "issue_d" in df.columns else pd.Timestamp.today()
            banking_df, reporting_date = enrich_banking_view(df, reporting_date)

            print(f"Date d'arrete: {reporting_date.date()}")
            print(f"Nombre de prets: {len(banking_df):,}")
            print(f"EAD total: {banking_df['EAD'].sum()/1e6:,.1f} M$")
            print(f"ECL baseline: {banking_df['ECL_ifrs9'].sum()/1e6:,.1f} M$")
            banking_df.head()
            """
        ),
        markdown_cell(
            """
            ## 2. Segmentation reglementaire et RWA

            La segmentation permet de sortir du simple portefeuille agrege. Elle porte la logique
            Bale: chaque segment a un risk weight et contribue differemment au RWA.
            """
        ),
        code_cell(
            """
            seg = segment_summary(banking_df)
            seg.to_csv(RESULTS_DIR / "regulatory_segment_summary.csv", index=False)
            seg
            """
        ),
        code_cell(
            """
            basel_metrics = compute_basel_metrics(banking_df, cet1_ratio=0.12)
            basel_df = pd.DataFrame([basel_metrics])
            basel_df.to_csv(RESULTS_DIR / "basel_capital_metrics.csv", index=False)
            basel_df.T
            """
        ),
        markdown_cell(
            """
            ## 3. Stress testing a 1 an: perte, CET1 et decision

            Le coeur bancaire du stress testing est la question suivante:
            si un choc arrive l'annee prochaine, combien la banque doit provisionner,
            est-ce que le CET1 resiste, et quelle action doit etre declenchee?
            """
        ),
        code_cell(
            """
            rows = []
            for scenario_key, scenario in ACTIVE_STRESS_SCENARIOS.items():
                projection, stage_projection = compute_dynamic_projection(
                    banking_df,
                    scenario,
                    horizon_years=1,
                    profile="front_loaded",
                    cet1_initial=0.12,
                    tax_rate=0.30,
                    scenario_name=scenario_key,
                )
                row = projection.iloc[0].to_dict()
                shortfall = max((7.0 - row["CET1_%"]) / 100 * row["RWA_M$"], 0)
                rows.append({
                    "scenario_key": scenario_key,
                    "Scenario": SCENARIO_LABELS.get(scenario_key, scenario_key),
                    "Expected_loss_Y1_M$": row["Annual_provision_M$"],
                    "ECL_Y1_M$": row["ECL_M$"],
                    "RWA_Y1_M$": row["RWA_M$"],
                    "CET1_post_stress_%": row["CET1_%"],
                    "PD_mean_%": row["PD_mean_%"],
                    "LGD_mean_%": row["LGD_mean_%"],
                    "Stage3_%": stage_projection.iloc[0]["Stage 3_%"],
                    "Capital_shortfall_7pct_M$": round(shortfall, 2),
                    "Management_action": capital_actions_from_shortfall(row["CET1_%"], shortfall),
                })

            stress_matrix = pd.DataFrame(rows).sort_values("CET1_post_stress_%")
            stress_matrix.to_csv(RESULTS_DIR / "one_year_stress_decision_matrix.csv", index=False)
            stress_matrix
            """
        ),
        markdown_cell(
            """
            ## 4. Projection dynamique T1-T5

            Cette section montre la trajectoire pluriannuelle d'un scenario severe: macro,
            ECL, RWA, CET1 et migration de stages. Elle repond a la critique du calcul
            uniquement total et non temporel.
            """
        ),
        code_cell(
            """
            projection, stage_projection = compute_dynamic_projection(
                banking_df,
                ACTIVE_STRESS_SCENARIOS["crisis_2008"],
                horizon_years=5,
                profile="front_loaded",
                cet1_initial=0.12,
                tax_rate=0.30,
                scenario_name="crisis_2008_expert",
            )
            projection.to_csv(RESULTS_DIR / "dynamic_projection_expert.csv", index=False)
            stage_projection.to_csv(RESULTS_DIR / "dynamic_stage_projection_expert.csv", index=False)
            projection
            """
        ),
        code_cell(
            """
            stage_projection
            """
        ),
        markdown_cell(
            """
            ## 5. Gouvernance: model registry et audit trail

            Une plateforme bancaire doit tracer la version des modeles, le statut de validation,
            le scenario execute et les sorties principales.
            """
        ),
        code_cell(
            """
            registry = ensure_model_registry()
            registry
            """
        ),
        code_cell(
            """
            worst = stress_matrix.iloc[0]
            run_id = log_audit_event(
                event_type="notebook_08_banking_expert_review",
                user="notebook_user",
                parameters={
                    "reporting_date": str(reporting_date.date()),
                    "n_scenarios": len(stress_matrix),
                    "capital_framework": "Basel standardized simplified",
                },
                outputs={
                    "worst_scenario": worst["Scenario"],
                    "expected_loss_y1_m": worst["Expected_loss_Y1_M$"],
                    "cet1_post_stress_pct": worst["CET1_post_stress_%"],
                    "management_action": worst["Management_action"],
                },
            )
            print(f"Run audite: {run_id}")
            load_audit_log(limit=10)
            """
        ),
        markdown_cell(
            """
            ## Conclusion bancaire

            Le projet couvre maintenant une chaine complete:

            macro scenario -> PD/LGD/EAD -> ECL -> RWA -> CET1 -> decision management -> audit trail.

            Les limites a expliquer restent: risk weights simplifiees, donnees Lending Club non bancaires
            au sens prudentiel complet, absence de vraie base comptable et calibration encore academique.
            """
        ),
    ]
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "pygments_lexer": "ipython3",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def generate_notebook() -> Path:
    NOTEBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTEBOOK_PATH.write_text(
        json.dumps(build_notebook(), ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    return NOTEBOOK_PATH


def append_result_summary_to_notebook(notebook_path: Path) -> None:
    """Ajoute une synthese visible meme avant re-execution du notebook."""
    if not notebook_path.exists():
        return
    try:
        basel = pd.read_csv(RESULTS_DIR / "basel_capital_metrics.csv")
        stress = pd.read_csv(RESULTS_DIR / "one_year_stress_decision_matrix.csv")
        projection = pd.read_csv(RESULTS_DIR / "dynamic_projection_expert.csv")
    except FileNotFoundError:
        return

    basel_cols = ["EAD_M$", "RWA_M$", "RWA_density_%", "CET1_ratio_%", "Total_capital_ratio_%", "Leverage_ratio_%"]
    stress_cols = ["Scenario", "Expected_loss_Y1_M$", "CET1_post_stress_%", "Capital_shortfall_7pct_M$", "Management_action"]
    projection_cols = ["year", "ECL_M$", "RWA_M$", "CET1_%", "PD_mean_%", "UNRATE", "GDPC1_growth"]

    summary = f"""
## Resultats generes automatiquement

Cette synthese est inseree par `scripts/generate_banking_expert_review.py` pour que
les resultats soient visibles dans le notebook meme avant re-execution.

### Capital stack Bale

```text
{basel[basel_cols].to_string(index=False)}
```

### Matrice stress testing a 1 an - scenarios les plus critiques

```text
{stress[stress_cols].head(7).to_string(index=False)}
```

### Projection dynamique T1-T5 - crise 2008

```text
{projection[projection_cols].to_string(index=False)}
```
"""

    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    notebook["cells"].insert(1, markdown_cell(summary))
    notebook_path.write_text(
        json.dumps(notebook, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )


def load_banking_input() -> pd.DataFrame:
    """Charge uniquement les colonnes utiles pour eviter les copies memoire lourdes."""
    df_full = pd.read_parquet(OUTPUT_DIR / "loan_clean.parquet")
    ecl = pd.read_parquet(OUTPUT_DIR / "ecl_baseline.parquet")
    cols = [c for c in BANKING_INPUT_COLS if c in df_full.columns]
    df = df_full[cols].copy()
    df["PD_pred"] = ecl["PD_pred"].values
    df["ECL_ifrs9"] = ecl["ECL_ifrs9"].values
    return df


def generate_banking_expert_outputs() -> dict:
    from src.banking_core import (
        capital_actions_from_shortfall,
        compute_basel_metrics,
        enrich_banking_view,
        ensure_model_registry,
        log_audit_event,
        segment_summary,
    )
    from src.scenario_projection import compute_dynamic_projection
    from src.stress_scenarios import ACTIVE_STRESS_SCENARIOS, SCENARIO_LABELS

    df = load_banking_input()
    reporting_date = pd.to_datetime(df["issue_d"]).max() if "issue_d" in df.columns else pd.Timestamp.today()
    banking_df, reporting_date = enrich_banking_view(df, reporting_date)

    seg = segment_summary(banking_df)
    seg_path = RESULTS_DIR / "regulatory_segment_summary.csv"
    seg.to_csv(seg_path, index=False)

    basel = pd.DataFrame([compute_basel_metrics(banking_df, cet1_ratio=0.12)])
    basel_path = RESULTS_DIR / "basel_capital_metrics.csv"
    basel.to_csv(basel_path, index=False)

    rows = []
    for scenario_key, scenario in ACTIVE_STRESS_SCENARIOS.items():
        projection, stage_projection = compute_dynamic_projection(
            banking_df,
            scenario,
            horizon_years=1,
            profile="front_loaded",
            cet1_initial=0.12,
            tax_rate=0.30,
            scenario_name=scenario_key,
        )
        row = projection.iloc[0].to_dict()
        shortfall = max((7.0 - row["CET1_%"]) / 100 * row["RWA_M$"], 0)
        rows.append({
            "scenario_key": scenario_key,
            "Scenario": SCENARIO_LABELS.get(scenario_key, scenario_key),
            "Expected_loss_Y1_M$": row["Annual_provision_M$"],
            "ECL_Y1_M$": row["ECL_M$"],
            "RWA_Y1_M$": row["RWA_M$"],
            "CET1_post_stress_%": row["CET1_%"],
            "PD_mean_%": row["PD_mean_%"],
            "LGD_mean_%": row["LGD_mean_%"],
            "Stage3_%": stage_projection.iloc[0]["Stage 3_%"],
            "Capital_shortfall_7pct_M$": round(shortfall, 2),
            "Management_action": capital_actions_from_shortfall(row["CET1_%"], shortfall),
        })
    stress = pd.DataFrame(rows).sort_values("CET1_post_stress_%")
    stress_path = RESULTS_DIR / "one_year_stress_decision_matrix.csv"
    stress.to_csv(stress_path, index=False)

    projection, stage_projection = compute_dynamic_projection(
        banking_df,
        ACTIVE_STRESS_SCENARIOS["crisis_2008"],
        horizon_years=5,
        profile="front_loaded",
        cet1_initial=0.12,
        tax_rate=0.30,
        scenario_name="crisis_2008_expert",
    )
    projection_path = RESULTS_DIR / "dynamic_projection_expert.csv"
    stage_path = RESULTS_DIR / "dynamic_stage_projection_expert.csv"
    projection.to_csv(projection_path, index=False)
    stage_projection.to_csv(stage_path, index=False)

    registry = ensure_model_registry()
    worst = stress.iloc[0]
    run_id = log_audit_event(
        event_type="script_banking_expert_review",
        user="pipeline",
        parameters={"reporting_date": str(reporting_date.date()), "n_scenarios": len(stress)},
        outputs={
            "worst_scenario": worst["Scenario"],
            "expected_loss_y1_m": worst["Expected_loss_Y1_M$"],
            "cet1_post_stress_pct": worst["CET1_post_stress_%"],
        },
    )

    notebook_path = generate_notebook()
    append_result_summary_to_notebook(notebook_path)

    return {
        "notebook": str(notebook_path),
        "segment_summary": str(seg_path),
        "basel_metrics": str(basel_path),
        "stress_matrix": str(stress_path),
        "dynamic_projection": str(projection_path),
        "dynamic_stage_projection": str(stage_path),
        "model_registry_rows": len(registry),
        "audit_run_id": run_id,
    }


if __name__ == "__main__":
    result = generate_banking_expert_outputs()
    for key, value in result.items():
        print(f"{key}: {value}")
