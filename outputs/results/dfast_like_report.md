# Rapport DFAST-like - Prototype IFRS 9 Stress Testing

## 1. Resume executif
Ce rapport consolide les sorties du moteur IFRS 9 stress testing sous un format inspire des dossiers DFAST/CCAR: portefeuille, scenarios, methodologie, pertes, capital, reverse stress test et gouvernance modele.

- Scenario le plus severe: Crise COVID-19 (ECL lift 2.64)
- Scenarios critiques CET1: 5/7
- Nature du rapport: prototype academique, non reporting reglementaire officiel.

## 2. Portefeuille et donnees
Le portefeuille est derive de Lending Club. Les variables macroeconomiques proviennent de FRED. Le capital CET1/RWA reste parametre par hypotheses pedagogiques sauf integration ulterieure de donnees banque/FFIEC.

## 3. Scenarios macroeconomiques
| scenario_key | scenario | scenario_type | narrative | UNRATE_delta | GDP_delta | HY_SPREAD_delta | FEDFUNDS_delta | CPI_delta | severity_score | pd_lift_floor | economically_adverse |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| adverse | Adverse | macro | Ralentissement macroeconomique general avec hausse du chomage et spreads credit. | 2.5 | -2.5 | 2.0 | 1.0 | 1.0 | 0.332 | 1.597 | True |
| severe | Severe | macro | Scenario macro severe combinant contraction PIB, chomage eleve et tension credit. | 4.0 | -3.5 | 2.0 | 1.0 | 1.5 | 0.487 | 1.877 | True |
| rate_shock | Choc Taux | taux | Hausse brutale des taux et de l'inflation, pression forte sur LGD/EAD. | 1.0 | -1.5 | 3.0 | 3.0 | 3.0 | 0.266 | 1.479 | True |
| market_2018 | Choc Marche 2018 | marche | Stress marche modere centre sur les spreads credit, sans recession profonde. | -0.1 | 0.0 | 1.7999999999999998 | -0.1 | -0.1 | 0.024 | 1.043 | True |
| ukraine_2022 | Inflation Ukraine 2022 | geopolitique_inflation | Choc inflation/geopolitique: taux et prix eleves, tension credit sans choc chomage majeur. | -0.2999999999999998 | -0.1 | 2.2 | 1.5999999999999996 | 6.0 | 0.133 | 1.238 | True |
| crisis_2008 | Crise 2008 | historique | Rejeu de la crise financiere mondiale, scenario historique systemique. | 6.0 | -6.3 | 15.0 | -2.25 | -2.4 | 0.898 | 2.616 | True |
| covid_2020 | Crise COVID-19 | historique | Choc sanitaire extreme, rupture rapide activite/chomage et forte incertitude. | 10.7 | -11.0 | 5.300000000000001 | -2.25 | -1.8 | 1.173 | 3.112 | True |

## 4. Methodologie modele
- PD baseline: modeles de classification compares avec AUC, Gini, KS, Brier, PSI et LogLoss.
- LGD/EAD: composantes construites en preprocessing puis stressees par sensibilites macro/taux.
- Stress ECL: PD_stressed x LGD_stressed x EAD_stressed avec garde-fou ECL >= baseline.
- Migration IFRS 9: matrice Markov stressee selon la severite macro.
- Capital: impact des pertes nettes d'impot sur CET1 et shortfall aux seuils 4.5% et 7%.

### Performance PD
| Model | AUC-ROC | Gini | KS | Brier | PSI | LogLoss |
| --- | --- | --- | --- | --- | --- | --- |
| LogReg | 0.6735 | 0.347 | 0.25 | 0.2834 | 0.0797 | 0.7793 |
| RandomForest | 0.6928 | 0.3857 | 0.2899 | 0.2082 | 0.0674 | 0.599 |
| XGBoost | 0.6742 | 0.3484 | 0.252 | 0.4029 | 0.102 | 1.0585 |
| LightGBM | 0.6808 | 0.3617 | 0.2643 | 0.2291 | 0.009 | 0.6447 |

## 5. Resultats pertes sous stress
| Scenario | ECL_stressed_M$ | ECL_baseline_M$ | ΔECL_M$ | ECL_lift | Coverage_% | PD_baseline_% | PD_stressed_% | PD_final_lift | PD_model_lift | PD_floor_lift | Severity_score | LGD_stressed_% | EAD_Mrd$ | Coherent_stress |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Adverse | 7764.06 | 3803.04 | 3961.03 | 2.04 | 22.83 | 45.27 | 83.22 | 2.087 | 2.087 | 1.597 | 0.332 | 66.25 | 35.19 | True |
| Severe | 8431.24 | 3803.04 | 4628.2 | 2.22 | 24.79 | 45.27 | 88.57 | 2.464 | 2.464 | 1.877 | 0.487 | 67.57 | 35.7 | True |
| Choc Taux | 8726.36 | 3803.04 | 4923.32 | 2.29 | 25.66 | 45.27 | 86.08 | 2.269 | 2.269 | 1.479 | 0.266 | 72.48 | 35.36 | True |
| Choc Marche 2018 | 4132.79 | 3803.04 | 329.75 | 1.09 | 12.15 | 45.27 | 48.33 | 1.068 | 1.068 | 1.043 | 0.024 | 60.39 | 34.0 | True |
| Inflation Ukraine 2022 | 6252.47 | 3803.04 | 2449.43 | 1.64 | 18.39 | 45.27 | 66.06 | 1.469 | 1.469 | 1.238 | 0.133 | 66.28 | 34.55 | True |
| Crise 2008 | 9589.22 | 3803.04 | 5786.18 | 2.52 | 28.2 | 45.27 | 93.37 | 3.106 | 3.106 | 2.616 | 0.898 | 73.34 | 36.04 | True |
| Crise COVID-19 | 10042.99 | 3803.04 | 6239.95 | 2.64 | 29.53 | 45.27 | 96.1 | 3.841 | 3.841 | 3.112 | 1.173 | 71.82 | 37.64 | True |

## 6. Capital, shortfall et actions managériales
| Scenario | CET1_initial_% | ECL_baseline_M$ | ECL_stressed_M$ | ΔECL_M$ | ΔECL_net_M$ | ΔCET1_% | CET1_post_stress_% | RWA_M$ | Capital_initial_M$ | Capital_post_M$ | Shortfall_4_5_M$ | Shortfall_7_0_M$ | zone | color | management_action | is_critical |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Adverse | 12.0 | 3803.04 | 7764.06 | 3961.03 | 2772.72 | -8.15 | 3.85 | 34004.21 | 4080.51 | 1307.79 | 222.4 | 1072.51 | 🚨 Critique (CET1 < 4.5% — Bâle III) | red | Plan de recapitalisation: injection capital, cession actifs risques, reduction origination. | True |
| Severe | 12.0 | 3803.04 | 8431.24 | 4628.2 | 3239.74 | -9.53 | 2.47 | 34004.21 | 4080.51 | 840.76 | 689.43 | 1539.53 | 🚨 Critique (CET1 < 4.5% — Bâle III) | red | Plan de recapitalisation: injection capital, cession actifs risques, reduction origination. | True |
| Choc Taux | 12.0 | 3803.04 | 8726.36 | 4923.32 | 3446.33 | -10.14 | 1.86 | 34004.21 | 4080.51 | 634.18 | 896.01 | 1746.12 | 🚨 Critique (CET1 < 4.5% — Bâle III) | red | Plan de recapitalisation: injection capital, cession actifs risques, reduction origination. | True |
| Choc Marche 2018 | 12.0 | 3803.04 | 4132.79 | 329.75 | 230.83 | -0.68 | 11.32 | 34004.21 | 4080.51 | 3849.68 | 0.0 | 0.0 | ✓ Résilient (CET1 ≥ 7%) | green | Surveillance normale et maintien des coussins. | False |
| Inflation Ukraine 2022 | 12.0 | 3803.04 | 6252.47 | 2449.43 | 1714.6 | -5.04 | 6.96 | 34004.21 | 4080.51 | 2365.9 | 0.0 | 14.39 | ⚠ Attention (4.5% ≤ CET1 < 7%) | orange | Plan de conservation capital: limiter dividendes, reduire croissance RWA, renforcer recouvrement. | False |
| Crise 2008 | 12.0 | 3803.04 | 9589.22 | 5786.18 | 4050.33 | -11.91 | 0.09 | 34004.21 | 4080.51 | 30.18 | 1500.01 | 2350.12 | 🚨 Critique (CET1 < 4.5% — Bâle III) | red | Plan de recapitalisation: injection capital, cession actifs risques, reduction origination. | True |
| Crise COVID-19 | 12.0 | 3803.04 | 10042.99 | 6239.95 | 4367.97 | -12.85 | -0.85 | 34004.21 | 4080.51 | -287.46 | 1817.65 | 2667.76 | 💥 Rupture (CET1 < 0% — Défaillance) | darkred | Resolution/restructuration: recapitalisation urgente ou plan de resolution. | True |

## 7. Reverse stress test
| intensity_critical | cet1_achieved_% | target_cet1_% | ECL_critical_M$ | ECL_baseline_M$ | ECL_lift | macro_critical |
| --- | --- | --- | --- | --- | --- | --- |
| 0.445 | 4.56 | 4.5 | 7419.12 | 3803.04 | 1.95 | {'UNRATE': 6.67, 'GDPC1_growth': -0.81, 'FEDFUNDS': 1.5, 'HY_SPREAD': 10.18, 'CPI_change': 0.93, 'DRCCLACBS': 4.4} |

## 8. Gouvernance et limites
| area | control | status | observation | recommended_action |
| --- | --- | --- | --- | --- |
| PD model | Discrimination champion | WATCH | Champion RandomForest avec AUC=0.693, Gini=0.386. | Presenter comme prototype academique; renforcer features ou calibration si objectif production. |
| PD model | Stabilite population | OK | PSI champion=0.067. Seuil usuel: <0.10 stable, 0.10-0.25 a surveiller. | Conserver la validation temporelle walk-forward et documenter la periode de test. |
| PD model | Calibration probabiliste | WATCH | Brier champion=0.208. Les probabilites restent pedagogiques. | Ajouter calibration Platt/isotonique et courbe de calibration pour une lecture bancaire stricte. |
| Stress testing | Coherence ECL/PD sous stress | OK | 7/7 scenarios coherents. | Conserver les controles automatiques dans validation_report.md. |
| Stress testing | Niveau PD moyen | WATCH | PD baseline moyenne=45.27%. Niveau eleve, typique d'un portefeuille Lending Club risque/filtre. | Expliquer que ce n'est pas un portefeuille bancaire prime; ajouter une calibration TTC si production. |
| Stress testing | Severite maximale | OK | Scenario le plus severe: Crise COVID-19 avec lift ECL=2.64. | Utiliser ce scenario pour commenter la sensibilite portefeuille et non comme prevision centrale. |
| Validation | Controles automatiques stress | OK | Statuts: {'OK': 7}. | Toute ligne REVIEW doit etre commentee dans le memoire. |
| Model governance | Champion stress testing | OK | Champion scoring: deterministic_sensitivity avec score=0.512. | Presenter la selection comme score multi-criteres: coherence, stabilite, precision, interpretabilite. |
| Model governance | Trace champion | OK | Champion documente: {'champion_model': 'deterministic_sensitivity', 'scenario_name': 'crisis_2008', 'selection_rule': 'max final_score', 'observed_target_dr': 0.0677}. | Garder ce fichier comme preuve de gouvernance modele. |
| Satellite macro | Pouvoir explicatif statistique | WATCH | Meilleur R2 satellite=-11.603. Les sorties actuelles montrent une faible qualite statistique. | Assumer le satellite comme outil de sensibilite economique; renforcer avec plus d'historique macro/defaut. |
| Satellite macro | Backtesting walk-forward | OK | 120 observations de backtesting disponibles. | Utiliser MAE/RMSE walk-forward plutot que le R2 seul pour la justification. |
| Capital | Impact CET1 | WATCH | 5/7 scenarios passent sous le seuil reglementaire CET1. | Presenter CET1/RWA comme hypothese pedagogique; remplacer par donnees banque si disponible. |
| Livrables | Couverture des livrables | OK | Couverture moyenne des piliers=100.0%. | Conserver outputs/results et outputs/figures pour la soutenance. |
| Execution | Portabilite environnement | OK | Configuration .venv locale coherente. | Recreer l'environnement avec scripts/setup_environment.ps1 avant demonstration. |

## 9. Conclusion prudentielle
Le prototype permet d'identifier les scenarios les plus penal en ECL, les zones de rupture CET1 et les reserves methodologiques. Pour une utilisation bancaire reelle, il faut ajouter donnees internes, capital reel, validation externe independante, monitoring et revue modele.