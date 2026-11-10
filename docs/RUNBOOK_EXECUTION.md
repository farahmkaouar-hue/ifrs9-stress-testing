# Runbook d'execution du projet IFRS 9 Stress Testing

## 1. Environnement

Si l'environnement virtuel est casse ou pointe vers un ancien utilisateur Windows,
utiliser le script portable :

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_environment.ps1
```

Alternative manuelle :

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 2. Cle FRED

Ne pas ecrire la cle FRED dans le code. La definir dans le terminal :

```powershell
$env:FRED_API_KEY = "VOTRE_CLE_FRED"
```

Pour rafraichir les CSV macro depuis FRED :

```powershell
.\.venv\Scripts\python.exe -c "from src.fred_client import refresh_macro_csvs; print(refresh_macro_csvs())"
```

## 3. Ordre d'execution des notebooks

Executer dans cet ordre pour eviter les incoherences de resultats :

```text
01_EDA.ipynb
02_Preprocessing.ipynb
03_Baseline_ECL.ipynb
04_Modeles_Satellites_Macro.ipynb
05_Stress_Testing.ipynb
06_Resilience_Reverse_Stress.ipynb
07_Stress_Testing_Validation_Avancee.ipynb
08_Banking_Expert_Review.ipynb
```

## 4. Rapport de validation

Le notebook `07_Stress_Testing_Validation_Avancee.ipynb` contient la section
`Pipeline final de validation bancaire et modelisation`.

Le notebook `08_Banking_Expert_Review.ipynb` doit etre execute apres le 07 pour
montrer les resultats attendus par un encadrant bancaire:

- date d'arrete du portefeuille ;
- segmentation reglementaire ;
- RWA et capital stack Bale ;
- stress testing a 1 an avec perte attendue, CET1 et action management ;
- projection dynamique T1-T5 ;
- model registry et audit trail.

En executant le notebook 07 jusqu'au bout, il regenere automatiquement :

```text
outputs/results/stress_model_comparison.csv
outputs/results/stress_model_champion.csv
outputs/results/project_evaluation.md
outputs/results/final_banking_modeling_audit.md
outputs/results/validation_report.md
outputs/results/basel_capital_metrics.csv
outputs/results/regulatory_segment_summary.csv
outputs/results/one_year_stress_decision_matrix.csv
outputs/results/dynamic_projection_expert.csv
outputs/results/dynamic_stage_projection_expert.csv
```

Execution manuelle optionnelle, uniquement pour debug :

```powershell
.\.venv\Scripts\python.exe scripts\run_final_pipeline.py
```

Pour recreer uniquement le notebook 08 et ses sorties:

```powershell
.\.venv\Scripts\python.exe scripts\generate_banking_expert_review.py
```

Pour realigner les anciens notebooks 01 a 07 avec la meme histoire bancaire:

```powershell
.\.venv\Scripts\python.exe scripts\align_notebooks_banking_story.py
```

Le check-up final doit etre lu avant soutenance. Les statuts `WATCH` ne bloquent
pas le prototype academique, mais ils doivent etre expliques: calibration PD,
niveau de risque Lending Club, hypotheses CET1/RWA et limites des satellites macro.

## 5. Tests metier rapides

Sans pytest :

```powershell
.\.venv\Scripts\python.exe scripts\run_business_tests.py
```

Avec pytest :

```powershell
.\.venv\Scripts\python.exe -m pytest tests
```

## 6. Dashboard

```powershell
.\.venv\Scripts\streamlit.exe run dashboard\app.py
```

Le dashboard contient maintenant un onglet `Validation` avec :

- validation metier des scenarios ;
- controles des sorties de stress ;
- ECL forward-looking ;
- comparaison des modeles satellites ;
- backtesting walk-forward ;
- migration Markov.

Il contient aussi un onglet `Bale & Gouvernance` avec RWA, capital stack,
shortfalls, model registry et audit trail.
