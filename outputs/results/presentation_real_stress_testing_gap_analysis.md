# Gap analysis - Presentation finale vs projet reel stress testing

Source analysee : `IFRS9_Presentation_Finale_v6.pptx`

## Decision globale

Le projet actuel couvre bien un prototype academique avance de stress testing IFRS 9 :

- EDA, preprocessing, qualite des donnees ;
- modeles PD baseline ;
- calcul ECL IFRS 9 ;
- scenarios adverse, severe, taux, marche 2018, crise 2008, COVID-19 ;
- stress PD/LGD/EAD ;
- migration Markov IFRS 9 ;
- forward-looking ECL ;
- resilience CET1 et reverse stress test ;
- dashboard Streamlit ;
- validation et check-up final bancaire/modelisation.

Pour correspondre exactement a la presentation et a un stress testing bancaire reel, il manque encore plusieurs briques fortes : donnees capital reelles FFIEC, validation externe Freddie Mac, API FastAPI, rapport DFAST complet, scenario Ukraine 2022, calibration PD plus stricte et gouvernance modele plus formelle.

## Mapping presentation -> projet

| Element de la presentation | Statut dans le projet | Commentaire |
|---|---|---|
| Choc macroeconomique | Fait | Scenarios adverse, severe, 2008, COVID, marche 2018. |
| Choc de taux | Fait | Scenario `rate_shock`, impact LGD/EAD et ECL. |
| Choc combine 2008 | Fait | Scenario `crisis_2008`, calibration historique FRED. |
| ECL = PD_stressed x LGD_stressed x EAD_stressed | Fait | Moteur `src/stress_scenarios.py`. |
| Reverse stress testing CET1 4.5% | Fait partiellement | Present, mais avec hypotheses CET1/RWA pedagogiques. |
| Desequilibre de la target | Fait partiellement | `class_weight`, `scale_pos_weight`, `is_unbalance`; SMOTE non integre par choix prudent. |
| Imputation KNN | Partiel | Le projet gere les valeurs manquantes, mais pas necessairement KNN partout. |
| SHAP values | Fait | Figures SHAP disponibles. |
| Walk-forward temporel | Fait | PD baseline et satellites macro. |
| Lending Club 2.26M, 2007-2018 | Fait selon donnees disponibles | Le projet utilise Lending Club. Verifier que le rapport final donne le volume exact apres filtres. |
| FRED macro variables | Fait | UNRATE, FEDFUNDS, CPI, GDP/GDPC1, HY spread, DRCCLACBS. |
| FFIEC Call Reports CET1 reel | Manquant | Actuellement `config/capital_assumptions.csv` contient des hypotheses. |
| Staging IFRS 9 Stage 1/2/3 | Fait | Staging et migration Markov. |
| XGBoost PD comme modele principal | Partiel | XGBoost existe, mais champion actuel RandomForest selon AUC. |
| Modeles satellites PD/LGD/EAD | Partiel | PD et LGD satellites presents; EAD reste surtout formule/CCF. |
| Calibration crise 2008-2009 | Fait partiellement | Scenarios et satellite calibres, mais pas backtesting externe strict. |
| Dashboard Streamlit | Fait | App integree avec onglet Validation. |
| Validation COVID-2020 | Fait partiellement | Scenario COVID present; validation externe hors-echantillon non prouvee. |
| Guerre Ukraine 2022 | Manquant | Non integre comme scenario historique. |
| API FastAPI | Manquant | Pas d'API de scoring/stress exposee. |
| Rapport DFAST | Manquant | Rapport de validation existe, mais pas format DFAST complet. |
| Freddie Mac 2019-2023 | Manquant | Aucune validation externe Freddie Mac. |
| AUC > 0.70 | Non atteint | Champion RandomForest AUC ~0.693. A presenter comme proche mais inferieur au seuil cible. |
| Erreur defaut simule vs reel < 2% | Non prouve | Pas de benchmark externe reel. |

## Ce qui manque pour coller exactement a la presentation

1. Ajouter une source FFIEC reelle pour CET1/RWA.
   - Remplacer `config/capital_assumptions.csv` par un fichier construit depuis FFIEC Call Reports.
   - Produire `outputs/results/ffiec_cet1_timeseries.csv`.
   - Ajouter une figure CET1 historique 2007-2018.

2. Ajouter validation externe Freddie Mac 2019-2023.
   - Charger un dataset externe.
   - Appliquer le modele ou recalibrer une cible comparable.
   - Produire AUC, KS, Brier, calibration et erreur defaut simule vs observe.

3. Ajouter scenario Ukraine 2022.
   - Definir un scenario macro 2022 : inflation, taux, spread, PIB.
   - Ajouter `ukraine_2022` dans `SCENARIOS`.
   - Regenerer stress, CET1, dashboard et validation.

4. Clarifier le modele champion PD.
   - La presentation annonce XGBoost.
   - Le projet retient RandomForest.
   - Deux options : modifier la presentation, ou forcer un choix XGBoost seulement si ses metriques deviennent meilleures apres tuning/calibration.

5. Ajouter calibration probabiliste plus forte.
   - Courbe de calibration.
   - Calibration Platt/isotonique.
   - Analyse Brier par periode.

6. Ajouter API FastAPI si la presentation la garde.
   - Endpoint `/score`.
   - Endpoint `/stress`.
   - Endpoint `/health`.
   - Sauvegarder exemples de requetes/reponses.

7. Ajouter un rapport DFAST-like.
   - Resume executif.
   - Description portefeuille.
   - Hypotheses macro.
   - Methodologie PD/LGD/EAD.
   - Resultats pertes et capital.
   - Gouvernance modele.
   - Limites et controles.

## Ce qui manque pour un stress testing bancaire reel

1. Donnees internes banque.
   - Historique defauts, recoveries, expositions, limites, collaterals.
   - Segmentation produit/region/secteur.
   - RWA et capital reel.

2. Definition precise du defaut.
   - 90 jours impayes, charge-off, restructuration, faillite.
   - Harmonisation avec IFRS 9/CRR/Bale.

3. Gouvernance modele.
   - Model owner.
   - Versioning.
   - Data lineage.
   - Validation independante.
   - Documentation des hypotheses.

4. Validation quantitative complete.
   - Backtesting par annee.
   - Calibration plots.
   - Lift/decile analysis.
   - Benchmark challenger.
   - Sensibilite et robustesse.

5. Validation economique des scenarios.
   - Coherence macroeconomique entre variables.
   - Probabilite/severite.
   - Narrative scenario.
   - Approbation par comite risque.

6. Production/industrialisation.
   - Pipeline reproductible.
   - Logs.
   - Monitoring.
   - Tests CI.
   - Environnement stable.
   - API ou batch scheduler.

## Recommandation soutenance

Ne dites pas que le projet est un stress testing bancaire de production.

Formulation recommandee :

> Le projet realise un prototype academique avance et auditable d'un moteur IFRS 9 de stress testing. Il couvre la chaine donnees -> PD/LGD/EAD -> ECL -> scenarios macro -> migration IFRS 9 -> CET1 -> reverse stress test -> dashboard. Les limites principales pour une mise en production bancaire sont l'absence de donnees internes banque, de capital FFIEC reel integre, de validation externe Freddie Mac et de gouvernance modele independante.

## Priorites si vous voulez rapprocher le projet de la presentation

1. Corriger la presentation pour ne pas promettre ce qui n'est pas implemente.
2. Ajouter scenario Ukraine 2022.
3. Ajouter une validation externe simple, meme sous forme benchmark.
4. Ajouter une figure/section calibration PD.
5. Ajouter un rapport DFAST-like.
6. Ajouter une API FastAPI seulement si le temps le permet.
