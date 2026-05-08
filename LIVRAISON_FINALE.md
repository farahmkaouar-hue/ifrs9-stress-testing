# Livraison finale - Projet IFRS 9 Stress Testing Bancaire

## Statut

Decision interne: **GO pour soutenance avec reserves explicites**.

Le projet est livre comme prototype academique avance de plateforme bancaire:

```text
Donnees -> Qualite -> PD/LGD/EAD -> ECL IFRS 9 -> Satellites macro
-> Stress testing 1 an -> Projection T1-T5 -> RWA/CET1 -> Decision -> Gouvernance
```

## A ouvrir en priorite

1. `README.md`  
   Vue generale du projet, structure et execution.

2. `RUNBOOK_EXECUTION.md`  
   Ordre exact d'execution et commandes de regeneration.

3. `notebooks/01_EDA.ipynb` a `notebooks/08_Banking_Expert_Review.ipynb`  
   Les notebooks sont alignes narrativement. Le notebook 08 consolide la vue bancaire experte.

4. `dashboard/app.py`  
   Application Streamlit avec portefeuille, stress testing, projection dynamique, Bale et gouvernance.

5. `outputs/results/validation_report.md`  
   Rapport de validation consolide.

6. `outputs/results/final_banking_modeling_audit.md`  
   Check-up final bancaire et modelisation.

## Resultats finaux importants

| Fichier | Role |
|---|---|
| `outputs/results/one_year_stress_decision_matrix.csv` | Perte attendue a 1 an, CET1 post-stress et action management par scenario. |
| `outputs/results/basel_capital_metrics.csv` | RWA, CET1, Tier 1, Total Capital, Leverage et shortfalls. |
| `outputs/results/regulatory_segment_summary.csv` | Segmentation reglementaire et densite RWA. |
| `outputs/results/dynamic_projection_expert.csv` | Projection T1-T5 ECL/RWA/CET1 sous crise 2008. |
| `outputs/results/dynamic_stage_projection_expert.csv` | Migration dynamique IFRS 9 par stage. |
| `outputs/governance/model_registry.csv` | Registre des modeles. |
| `outputs/governance/audit_log.jsonl` | Audit trail des executions. |

## Commandes de regeneration

Recreer l'environnement:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_environment.ps1
```

Pipeline final complet:

```powershell
.\.venv\Scripts\python.exe scripts\run_final_pipeline.py
```

Tests metier:

```powershell
.\.venv\Scripts\python.exe scripts\run_business_tests.py
```

Dashboard:

```powershell
.\.venv\Scripts\streamlit.exe run dashboard\app.py
```

## Points a annoncer a l'encadrante

- Le portefeuille Lending Club est plus risque qu'un portefeuille bancaire prime; les PD moyennes elevees doivent etre interpretees dans ce contexte.
- Les RWA/CET1 sont une approximation pedagogique basee sur des risk weights simplifiees, pas une declaration reglementaire officielle.
- Les modeles satellites macro servent de mecanisme forward-looking et de sensibilite economique; une production bancaire exigerait plus d'historique et une validation externe.
- Les scenarios historiques/reglementaires sont verrouilles; seul le scenario personnalise est modifiable.
- La gouvernance est simulee mais auditable: model registry, audit trail, rapports de validation et decision management.

## Nettoyage effectue

- Suppression de `.venv/` locale cassee.
- Suppression de `.claude/` local.
- Suppression des `__pycache__` du code projet.
- Ajout des exclusions de livraison dans `.gitignore`.
- Conservation des sorties utiles dans `outputs/results`, `outputs/governance`, `outputs/documents` et `outputs/presentations`.

Note: `outputs/tmpyj2sx5pn` est un dossier temporaire verrouille par Windows. Il est ignore par `.gitignore`; s'il reste visible localement, il peut etre supprime manuellement apres fermeture de tous les processus qui l'utilisent.
