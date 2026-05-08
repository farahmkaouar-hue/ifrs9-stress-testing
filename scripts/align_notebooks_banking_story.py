"""
align_notebooks_banking_story.py - Harmonise les notebooks 01 a 07.

Objectif: rendre l'histoire du projet coherente pour une revue encadrante:
EDA -> preprocessing -> ECL IFRS 9 -> satellites macro -> stress testing
-> resilience Bale -> validation/gouvernance -> revue experte notebook 08.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTEBOOKS_DIR = ROOT / "notebooks"

TAG = "banking_coherence"


NOTEBOOK_GUIDANCE = {
    "01_EDA.ipynb": {
        "role": "Comprendre le portefeuille, la qualite des donnees, les defauts, les vintages et les variables utiles avant toute modelisation.",
        "expert_view": "Une banque commence par une photographie fiable du portefeuille: population, defauts, maturite, censure, distributions et anomalies.",
        "outputs": "schema_quality_report, missing_by_year, vintage_default_profile, figures EDA.",
        "next_step": "Le notebook 02 transforme cette exploration en dataset propre, datable et utilisable pour IFRS 9.",
    },
    "02_Preprocessing.ipynb": {
        "role": "Construire le portefeuille analytique: nettoyage, encodage, date d'octroi, LGD, EAD, stage IFRS 9 et fusion macro.",
        "expert_view": "Le point critique est d'eviter le data leakage et de conserver les variables necessaires a une vue a date d'arrete.",
        "outputs": "loan_clean.parquet, rapports qualite, dictionnaire macro FRED.",
        "next_step": "Le notebook 03 utilise ce portefeuille propre pour modeliser la PD et calculer l'ECL baseline.",
    },
    "03_Baseline_ECL.ipynb": {
        "role": "Modeliser la PD, comparer les modeles, calculer ECL IFRS 9 baseline par pret, stage et segment.",
        "expert_view": "IFRS 9 exige une estimation de pertes attendues. La baseline sert de reference avant stress et avant impact capital.",
        "outputs": "ecl_baseline.parquet, modeles PD, metriques, SHAP.",
        "next_step": "Le notebook 04 relie les variables macro aux pertes via les modeles satellites.",
    },
    "04_Modeles_Satellites_Macro.ipynb": {
        "role": "Relier cycle economique et risque credit: chomage, PIB, taux, spreads, inflation et delinquence.",
        "expert_view": "Le stress testing bancaire doit expliquer comment un choc macro devient une hausse de PD/LGD/EAD.",
        "outputs": "satellite_pd_comparison.csv, satellite_pd_walk_forward.csv, variables macro validees.",
        "next_step": "Le notebook 05 applique des scenarios de choc cohérents aux parametres de risque.",
    },
    "05_Stress_Testing.ipynb": {
        "role": "Tester plusieurs scenarios de crise et mesurer la perte/provision attendue a 1 an.",
        "expert_view": "Une crise historique doit etre verrouillee; seul un scenario personnalise est modifiable. Le resultat central est: perte Y1, ECL, PD/LGD/EAD et decision de resistance.",
        "outputs": "stress_ecl_summary.csv, one_year_stress_decision_matrix.csv.",
        "next_step": "Le notebook 06 traduit ces pertes en impact CET1, shortfall et actions de management.",
    },
    "06_Resilience_Reverse_Stress.ipynb": {
        "role": "Mesurer la resilience capital: CET1, RWA, shortfall, reverse stress test et point de rupture.",
        "expert_view": "Bale regarde la solvabilite: RWA, capital stack, seuils et actions de remediation si la banque ne resiste pas.",
        "outputs": "cet1_resilience_table.csv, resilience_curve.csv, reverse_stress_test.csv, basel_capital_metrics.csv.",
        "next_step": "Le notebook 07 consolide validation, gouvernance modele et coherence des sorties.",
    },
    "07_Stress_Testing_Validation_Avancee.ipynb": {
        "role": "Valider la coherence metier: scenarios, sorties de stress, migration Markov, backtesting et evaluation projet.",
        "expert_view": "Une plateforme bancaire doit etre auditable: controles, model registry, audit trail et limites de production.",
        "outputs": "validation_report.md, final_banking_modeling_audit.md, model_registry, audit_log.",
        "next_step": "Le notebook 08 presente la revue bancaire experte complete et les resultats de decision.",
    },
}


def markdown_cell(source: str, position: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {"tags": [TAG], "banking_coherence_position": position},
        "source": source.strip().splitlines(True),
    }


def code_cell(source: str, position: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {"tags": [TAG], "banking_coherence_position": position},
        "outputs": [],
        "source": source.strip().splitlines(True),
    }


def intro_text(name: str, guidance: dict) -> str:
    return f"""
## Positionnement bancaire du notebook

**Role dans la plateforme**  
{guidance["role"]}

**Lecture expert bancaire**  
{guidance["expert_view"]}

**Sorties attendues**  
{guidance["outputs"]}

**Transition logique**  
{guidance["next_step"]}
"""


def closing_text(name: str) -> str:
    return f"""
## Coherence avec la chaine IFRS 9 + Bale + stress testing

Ce notebook s'inscrit dans la chaine complete:

`Donnees -> Qualite -> PD/LGD/EAD -> ECL IFRS 9 -> Satellites macro -> Stress Y1 -> RWA/CET1 -> Decision -> Gouvernance`

Les resultats finaux de niveau bancaire sont consolides dans:

- `notebooks/08_Banking_Expert_Review.ipynb`
- `outputs/results/one_year_stress_decision_matrix.csv`
- `outputs/results/basel_capital_metrics.csv`
- `outputs/results/regulatory_segment_summary.csv`
- `outputs/results/dynamic_projection_expert.csv`

Cette coherence permet de defendre le projet a la fois comme travail de modelisation
et comme prototype de plateforme bancaire.
"""


def stress_bridge_code() -> str:
    return """
from pathlib import Path
import pandas as pd

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
stress_decision_path = ROOT / "outputs" / "results" / "one_year_stress_decision_matrix.csv"

if stress_decision_path.exists():
    stress_decision = pd.read_csv(stress_decision_path)
    display(stress_decision)
else:
    print("Sortie non disponible. Executer scripts/generate_banking_expert_review.py ou le notebook 08.")
"""


def basel_bridge_code() -> str:
    return """
from pathlib import Path
import pandas as pd

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
basel_path = ROOT / "outputs" / "results" / "basel_capital_metrics.csv"
segment_path = ROOT / "outputs" / "results" / "regulatory_segment_summary.csv"

if basel_path.exists():
    display(pd.read_csv(basel_path).T)
else:
    print("basel_capital_metrics.csv non disponible.")

if segment_path.exists():
    display(pd.read_csv(segment_path))
else:
    print("regulatory_segment_summary.csv non disponible.")
"""


def governance_bridge_code() -> str:
    return """
from pathlib import Path
import pandas as pd

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
registry_path = ROOT / "outputs" / "governance" / "model_registry.csv"
audit_path = ROOT / "outputs" / "governance" / "audit_log.jsonl"

if registry_path.exists():
    display(pd.read_csv(registry_path))
else:
    print("Model registry non disponible. Executer le notebook 08.")

if audit_path.exists():
    audit = pd.read_json(audit_path, lines=True)
    display(audit.tail(10))
else:
    print("Audit trail non disponible. Executer un stress run ou le notebook 08.")
"""


def extra_cells_for_notebook(name: str) -> list[dict]:
    if name == "05_Stress_Testing.ipynb":
        return [
            markdown_cell(
                """
## Controle bancaire complementaire: matrice stress testing a 1 an

Cette table repond a la question centrale du stress testing: combien la banque
perd l'annee prochaine sous chaque crise, quel est le CET1 post-stress et quelle
action de management est requise.
""",
                "bridge",
            ),
            code_cell(stress_bridge_code(), "bridge"),
        ]
    if name == "06_Resilience_Reverse_Stress.ipynb":
        return [
            markdown_cell(
                """
## Controle bancaire complementaire: RWA et capital stack Bale

Cette section relie la resilience CET1 aux RWA et aux ratios prudentiels.
Elle complete l'analyse de resilience par une lecture Bale.
""",
                "bridge",
            ),
            code_cell(basel_bridge_code(), "bridge"),
        ]
    if name == "07_Stress_Testing_Validation_Avancee.ipynb":
        return [
            markdown_cell(
                """
## Controle bancaire complementaire: gouvernance modele et audit trail

Cette section montre que les executions sont tracables et que les modeles ont
un statut de validation/approbation, meme dans un prototype academique.
""",
                "bridge",
            ),
            code_cell(governance_bridge_code(), "bridge"),
        ]
    return []


def align_notebook(path: Path) -> bool:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    cells = [
        cell
        for cell in notebook.get("cells", [])
        if TAG not in cell.get("metadata", {}).get("tags", [])
    ]
    guidance = NOTEBOOK_GUIDANCE[path.name]

    insertion_index = 1 if cells else 0
    cells.insert(insertion_index, markdown_cell(intro_text(path.name, guidance), "intro"))
    cells.extend(extra_cells_for_notebook(path.name))
    cells.append(markdown_cell(closing_text(path.name), "closing"))
    notebook["cells"] = cells
    path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1), encoding="utf-8")
    return True


def align_all_notebooks() -> list[Path]:
    updated = []
    for name in NOTEBOOK_GUIDANCE:
        path = NOTEBOOKS_DIR / name
        if path.exists():
            align_notebook(path)
            updated.append(path)
    return updated


if __name__ == "__main__":
    updated = align_all_notebooks()
    for path in updated:
        print(f"updated: {path}")
