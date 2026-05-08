# Projet IFRS 9 Stress Testing Bancaire

Ce projet construit un moteur IFRS 9 oriente stress testing bancaire: preparation du portefeuille Lending Club, modelisation PD/LGD/EAD, calcul ECL baseline, scenarios macroeconomiques, comparaison de plusieurs approches de stress, validation et dashboard Streamlit.

Pour la version finale a remettre, commencer par `LIVRAISON_FINALE.md`.

## Structure recommandee

| Dossier/Fichier | Role |
|---|---|
| `notebooks/01_EDA.ipynb` | Exploration initiale: distribution, qualite, defauts, variables metier. |
| `notebooks/02_Preprocessing.ipynb` | Nettoyage, encodage, feature engineering, LGD/EAD, fusion macro. |
| `notebooks/03_Baseline_ECL.ipynb` | Modeles PD et calcul ECL IFRS 9 baseline. |
| `notebooks/04_Modeles_Satellites_Macro.ipynb` | Modeles macro-satellites et sensibilites economiques. |
| `notebooks/05_Stress_Testing.ipynb` | Chocs macro, stress PD/LGD/EAD, ECL stressee. |
| `notebooks/06_Resilience_Reverse_Stress.ipynb` | Impact CET1, resilience et reverse stress test. |
| `notebooks/07_Stress_Testing_Validation_Avancee.ipynb` | Validation scenarios, Markov migration, forward-looking ECL, comparaison stress models. |
| `notebooks/08_Banking_Expert_Review.ipynb` | Revue experte bancaire/developpement: date d'arrete, segmentation, RWA, capital stack, stress testing 1 an, projection T1-T5, gouvernance et audit trail. |
| `src/` | Code reutilisable pour industrialiser les notebooks. |
| `scripts/` | Lancement de validations et generation de rapports. |
| `outputs/results/` | Rapports CSV/Markdown generes. |
| `dashboard/app.py` | Interface Streamlit de restitution. |

## Execution

1. Recreer l'environnement portable si necessaire:
   `powershell -ExecutionPolicy Bypass -File scripts/setup_environment.ps1`
2. Installer les dependances manuellement si vous n'utilisez pas le script:
   `pip install -r requirements.txt`
3. Optionnel pour FRED: definir `FRED_API_KEY` dans l'environnement.
4. Lancer les notebooks `01` a `08` dans l'ordre. Le notebook `07` execute la validation avancee et le notebook `08` montre la revue bancaire experte.
5. Lancer le dashboard: `streamlit run dashboard/app.py`

Les scripts restent executables separement pour debug, mais ils ne sont plus obligatoires si le notebook `07_Stress_Testing_Validation_Avancee.ipynb` a ete execute jusqu'au bout.

Pour realigner la narration bancaire des notebooks 01 a 07 apres modification:

`python scripts/align_notebooks_banking_story.py`

## Points forts modeling/stress testing

- Plusieurs modeles PD baseline peuvent etre compares.
- Plusieurs modeles satellites macro sont prevus pour relier le risque au cycle economique.
- Le stress testing ne se limite plus a un multiplicateur: il combine scenarios economiques, stress PD/LGD/EAD, Markov migration, forward-looking ECL, CET1 et reverse stress.
- Les controles EDA/preprocessing generent des fichiers auditables: schema, valeurs manquantes, outliers, vintage default profile, dictionnaire FRED et audit global.
- Le check-up final documente les reserves de gouvernance modele: niveau PD Lending Club, calibration, satellite macro, hypotheses CET1/RWA et environnement d'execution.
- Le notebook 08 documente la vue quasi-professionnelle: portefeuille a date d'arrete, segmentation reglementaire, RWA, capital stack, stress testing a 1 an, decision management et audit trail.

## Fichiers a ne pas versionner

Les dossiers `.venv/`, `__pycache__/`, sorties lourdes, donnees brutes et cles API ne doivent pas etre ajoutes a Git. La cle FRED doit rester dans la variable d'environnement `FRED_API_KEY`, jamais dans le code.
