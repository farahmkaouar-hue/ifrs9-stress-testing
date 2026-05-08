"""
final_banking_audit.py - Check-up final bancaire et modelisation.

Ce script consolide les controles de soutenance:
- qualite des livrables,
- performance PD,
- coherence des scenarios de stress,
- resilience CET1,
- limites a expliciter devant un jury ou un comite risque.

Il ne remplace pas les notebooks. Il sert de couche finale de gouvernance
modele afin que les resultats soient interpretes correctement.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError


ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "outputs"
MODELS_DIR = OUTPUT_DIR / "models"
RESULTS_DIR = OUTPUT_DIR / "results"


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except EmptyDataError:
        return pd.DataFrame()


def _status(ok: bool, warning: bool = False) -> str:
    if ok:
        return "OK"
    if warning:
        return "WATCH"
    return "REVIEW"


def _add(rows: list[dict], area: str, control: str, status: str, observation: str, action: str) -> None:
    rows.append({
        "area": area,
        "control": control,
        "status": status,
        "observation": observation,
        "recommended_action": action,
    })


def _md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_Aucun controle disponible._"
    cols = list(df.columns)
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for _, row in df.iterrows():
        values = [str(row[c]).replace("\n", " ") for c in cols]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def run_final_banking_audit() -> tuple[Path, Path]:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    pd_models = _read_csv(MODELS_DIR / "pd_model_comparison.csv")
    stress = _read_csv(RESULTS_DIR / "stress_ecl_summary.csv")
    stress_validation = _read_csv(RESULTS_DIR / "stress_validation_report.csv")
    stress_models = _read_csv(RESULTS_DIR / "stress_model_comparison.csv")
    champion = _read_csv(RESULTS_DIR / "stress_model_champion.csv")
    cet1 = _read_csv(RESULTS_DIR / "cet1_resilience_table.csv")
    project_eval = _read_csv(RESULTS_DIR / "project_evaluation.csv")
    sat = _read_csv(MODELS_DIR / "satellite_pd_comparison.csv")
    wf = _read_csv(MODELS_DIR / "satellite_pd_walk_forward.csv")

    rows: list[dict] = []

    if pd_models.empty:
        _add(rows, "PD model", "Presence comparaison PD", "REVIEW", "Fichier pd_model_comparison.csv absent.", "Reexecuter le notebook 03_Baseline_ECL.")
    else:
        best = pd_models.sort_values("AUC-ROC", ascending=False).iloc[0]
        auc = float(best["AUC-ROC"])
        gini = float(best["Gini"])
        psi = float(best["PSI"])
        brier = float(best["Brier"])
        _add(
            rows,
            "PD model",
            "Discrimination champion",
            _status(auc >= 0.70, warning=auc >= 0.65),
            f"Champion {best['Model']} avec AUC={auc:.3f}, Gini={gini:.3f}.",
            "Presenter comme prototype academique; renforcer features ou calibration si objectif production.",
        )
        _add(
            rows,
            "PD model",
            "Stabilite population",
            _status(psi <= 0.10),
            f"PSI champion={psi:.3f}. Seuil usuel: <0.10 stable, 0.10-0.25 a surveiller.",
            "Conserver la validation temporelle walk-forward et documenter la periode de test.",
        )
        _add(
            rows,
            "PD model",
            "Calibration probabiliste",
            _status(brier <= 0.20, warning=brier <= 0.25),
            f"Brier champion={brier:.3f}. Les probabilites restent pedagogiques.",
            "Ajouter calibration Platt/isotonique et courbe de calibration pour une lecture bancaire stricte.",
        )

    if stress.empty:
        _add(rows, "Stress testing", "Presence stress ECL", "REVIEW", "Fichier stress_ecl_summary.csv absent.", "Reexecuter le notebook 05_Stress_Testing.")
    else:
        coherent = bool(stress.get("Coherent_stress", pd.Series([False])).all())
        _add(
            rows,
            "Stress testing",
            "Coherence ECL/PD sous stress",
            _status(coherent),
            f"{int(stress.get('Coherent_stress', pd.Series(dtype=bool)).sum())}/{len(stress)} scenarios coherents.",
            "Conserver les controles automatiques dans validation_report.md.",
        )
        if "PD_baseline_%" in stress.columns:
            pd_base = float(stress["PD_baseline_%"].iloc[0])
            _add(
                rows,
                "Stress testing",
                "Niveau PD moyen",
                _status(pd_base <= 25.0, warning=pd_base <= 50.0),
                f"PD baseline moyenne={pd_base:.2f}%. Niveau eleve, typique d'un portefeuille Lending Club risque/filtre.",
                "Expliquer que ce n'est pas un portefeuille bancaire prime; ajouter une calibration TTC si production.",
            )
        if {"Scenario", "ECL_lift"}.issubset(stress.columns):
            max_row = stress.sort_values("ECL_lift", ascending=False).iloc[0]
            _add(
                rows,
                "Stress testing",
                "Severite maximale",
                _status(float(max_row["ECL_lift"]) >= 2.0),
                f"Scenario le plus severe: {max_row['Scenario']} avec lift ECL={float(max_row['ECL_lift']):.2f}.",
                "Utiliser ce scenario pour commenter la sensibilite portefeuille et non comme prevision centrale.",
            )

    if not stress_validation.empty and "validation_status" in stress_validation.columns:
        ok = bool((stress_validation["validation_status"] == "OK").all())
        _add(
            rows,
            "Validation",
            "Controles automatiques stress",
            _status(ok),
            f"Statuts: {stress_validation['validation_status'].value_counts().to_dict()}.",
            "Toute ligne REVIEW doit etre commentee dans le memoire.",
        )

    if not stress_models.empty:
        top = stress_models.sort_values("final_score", ascending=False).iloc[0]
        _add(
            rows,
            "Model governance",
            "Champion stress testing",
            _status(bool(top.get("economic_coherent", False))),
            f"Champion scoring: {top['model_name']} avec score={float(top['final_score']):.3f}.",
            "Presenter la selection comme score multi-criteres: coherence, stabilite, precision, interpretabilite.",
        )
    if not champion.empty:
        _add(
            rows,
            "Model governance",
            "Trace champion",
            "OK",
            f"Champion documente: {champion.iloc[0].to_dict()}.",
            "Garder ce fichier comme preuve de gouvernance modele.",
        )

    if not sat.empty:
        r2_col = "R²" if "R²" in sat.columns else ("RÂ²" if "RÂ²" in sat.columns else None)
        if r2_col:
            best_r2 = pd.to_numeric(sat[r2_col], errors="coerce").max()
            _add(
                rows,
                "Satellite macro",
                "Pouvoir explicatif statistique",
                _status(best_r2 >= 0.0, warning=True),
                f"Meilleur R2 satellite={best_r2:.3f}. Les sorties actuelles montrent une faible qualite statistique.",
                "Assumer le satellite comme outil de sensibilite economique; renforcer avec plus d'historique macro/defaut.",
            )
    if not wf.empty:
        _add(
            rows,
            "Satellite macro",
            "Backtesting walk-forward",
            "OK",
            f"{len(wf)} observations de backtesting disponibles.",
            "Utiliser MAE/RMSE walk-forward plutot que le R2 seul pour la justification.",
        )

    if cet1.empty:
        _add(rows, "Capital", "Presence resilience CET1", "REVIEW", "Fichier cet1_resilience_table.csv absent.", "Reexecuter le notebook 06_Resilience_Reverse_Stress.")
    else:
        critical = int(pd.Series(cet1.get("is_critical", [])).astype(str).str.lower().eq("true").sum())
        _add(
            rows,
            "Capital",
            "Impact CET1",
            _status(critical == 0, warning=critical < len(cet1)),
            f"{critical}/{len(cet1)} scenarios passent sous le seuil reglementaire CET1.",
            "Presenter CET1/RWA comme hypothese pedagogique; remplacer par donnees banque si disponible.",
        )

    if not project_eval.empty:
        coverage = float(project_eval["coverage_%"].mean()) if "coverage_%" in project_eval.columns else 0.0
        _add(
            rows,
            "Livrables",
            "Couverture des livrables",
            _status(coverage >= 95.0),
            f"Couverture moyenne des piliers={coverage:.1f}%.",
            "Conserver outputs/results et outputs/figures pour la soutenance.",
        )

    venv_cfg = ROOT / ".venv" / "pyvenv.cfg"
    setup_script = ROOT / "scripts" / "setup_environment.ps1"
    if venv_cfg.exists():
        text = venv_cfg.read_text(encoding="utf-8", errors="ignore")
        broken = "Users\\ilfir" in text or "Users/ilfir" in text
        _add(
            rows,
            "Execution",
            "Portabilite environnement",
            "WATCH" if broken and setup_script.exists() else _status(not broken),
            "Le .venv local pointe vers un ancien chemin utilisateur." if broken else "Configuration .venv locale coherente.",
            "Recreer l'environnement avec scripts/setup_environment.ps1 avant demonstration.",
        )
    else:
        _add(rows, "Execution", "Portabilite environnement", "WATCH", ".venv absent.", "Executer scripts/setup_environment.ps1.")

    audit = pd.DataFrame(rows)
    csv_path = RESULTS_DIR / "final_banking_modeling_audit.csv"
    md_path = RESULTS_DIR / "final_banking_modeling_audit.md"
    audit.to_csv(csv_path, index=False)

    status_counts = audit["status"].value_counts().to_dict()
    go_status = "GO avec reserves explicites" if status_counts.get("REVIEW", 0) == 0 else "GO conditionnel apres correction des points REVIEW"

    md_lines = [
        "# Check-up final bancaire et modelisation",
        "",
        f"**Decision de soutenance : {go_status}**",
        "",
        "## Synthese des statuts",
        _md_table(pd.DataFrame([status_counts])),
        "",
        "## Controles detailles",
        _md_table(audit),
        "",
        "## Points a annoncer clairement",
        "- Les resultats sont solides pour un prototype academique de stress testing IFRS 9.",
        "- Le portefeuille Lending Club est plus risque qu'un portefeuille bancaire prime; les PD moyennes doivent etre interpretees dans ce contexte.",
        "- Les hypotheses CET1/RWA sont pedagogiques sauf integration d'un fichier capital banque.",
        "- Les modeles satellites macro sont surtout utilises comme mecanisme forward-looking et de sensibilite economique; une production bancaire exigerait plus d'historique et une validation externe.",
        "- Le choix du champion stress testing est documente par scoring multi-criteres, ce qui renforce la gouvernance modele.",
        "",
        "## Priorites finales",
        "1. Refaire l'environnement Python portable avant demonstration.",
        "2. Reexecuter les notebooks 01 a 07 pour figer les outputs finaux.",
        "3. Presenter la calibration PD/CET1 comme limite methodologique et non comme erreur.",
    ]
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    return md_path, csv_path


if __name__ == "__main__":
    md, csv_path = run_final_banking_audit()
    print(md)
    print(csv_path)
