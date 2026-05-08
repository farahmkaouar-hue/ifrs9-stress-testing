# Rapport de validation - Stress Testing IFRS 9

**Statut global des controles stress : OK**

## 1. Evaluation globale du projet
| pillar | weight | score | coverage_% | missing | expert_comment |
| --- | --- | --- | --- | --- | --- |
| EDA | 10 | 10.0 | 100.0 |  | EDA couvre cible, segmentation, cycle macro et censure vintage. |
| Preprocessing | 12 | 12.0 | 100.0 |  | Pipeline auditable avec dictionnaire FRED et controles qualite. |
| Baseline ECL | 12 | 12.0 | 100.0 |  | PD individuelle, ECL baseline et validation temporelle presentes. |
| Satellites macro | 12 | 12.0 | 100.0 |  | Lien macro-PD explicite pour transformer les chocs en defaut attendu. |
| Stress testing | 16 | 16.0 | 100.0 |  | Plusieurs moteurs de stress sont compares et un champion est documente. |
| Scenarios historiques | 10 | 10.0 | 100.0 |  | COVID-19, marche 2018, crise 2008, adverse, severe et taux sont actifs. |
| Resilience CET1 | 10 | 10.0 | 100.0 |  | Impact capital et point de rupture sont disponibles. |
| Application | 10 | 10.0 | 100.0 |  | Dashboard Streamlit centralise portefeuille, stress, resilience et validation. |
| Communication | 8 | 8.0 | 100.0 |  | Trois presentations separees documentent methode, code et outputs. |

### Penalites de maturite restantes
| risk | points | action |
| --- | --- | --- |
| Capital/RWA encore pedagogique | 5 | Remplacer ou justifier les hypotheses CET1 avec donnees banque si disponibles. |
| Validation externe limitee | 3 | Ajouter benchmark externe ou stress historique supplementaire si le temps le permet. |
| Notebooks a reexecuter apres les derniers changements | 2 | Reexecuter 01 a 07 avant soutenance pour figer les sorties finales. |

### Check-up final bancaire et modelisation
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

## 2. Modeles PD individuels
| Model | AUC-ROC | Gini | KS | Brier | PSI | LogLoss |
| --- | --- | --- | --- | --- | --- | --- |
| LogReg | 0.6735 | 0.347 | 0.25 | 0.2834 | 0.0797 | 0.7793 |
| RandomForest | 0.6928 | 0.3857 | 0.2899 | 0.2082 | 0.0674 | 0.599 |
| XGBoost | 0.6742 | 0.3484 | 0.252 | 0.4029 | 0.102 | 1.0585 |
| LightGBM | 0.6808 | 0.3617 | 0.2643 | 0.2291 | 0.009 | 0.6447 |

## 3. Modeles satellites macro-PD
Le champion doit etre performant statistiquement et coherent economiquement.
| Model | R² | R²_adj | RMSE | MAE | AIC | BIC | DW | DW_ok | DR_base_check | DR_shock_check | economic_ok | stress_lift_check |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OLS | -19.4046 | -29.6069 | 0.0311 | 0.028 | -132.0 | -123.3 | 0.092 | ✗ Problème autocorrélation | 0.1064 | 0.2813 | True | 2.6425 |
| Ridge | -11.6034 | -17.905 | 0.0245 | 0.0212 |  |  | 0.14 | ✗ Problème autocorrélation | 0.1114 | 0.2745 | True | 2.4645 |
| LASSO | -13.3472 | -20.5208 | 0.0261 | 0.023 |  |  | 0.123 | ✗ Problème autocorrélation | 0.1099 | 0.2763 | True | 2.5146 |
| ElasticNet | -16.2219 | -24.8328 | 0.0286 | 0.0255 |  |  | 0.105 | ✗ Problème autocorrélation | 0.1081 | 0.279 | True | 2.5802 |
| RandomForestReg | -87.3823 | -131.5734 | 0.0648 | 0.0608 |  |  | 0.066 | ✗ Problème autocorrélation | 0.1653 | 0.2166 | True | 1.3102 |
| GradientBoostingReg | -89.2783 | -134.4174 | 0.0654 | 0.0614 |  |  | 0.069 | ✗ Problème autocorrélation | 0.1625 | 0.206 | True | 1.2673 |
| XGBoostReg | -89.7727 | -135.159 | 0.0656 | 0.0609 |  |  | 0.092 | ✗ Problème autocorrélation | 0.1574 | 0.2138 | True | 1.3579 |

## 4. Backtesting walk-forward satellite
| Model | MAE | RMSE | n_folds |
| --- | --- | --- | --- |
| OLS | 0.0237410642842641 | 0.028041405187570853 | 30 |
| ElasticNet | 0.02383093791069175 | 0.028043303649377925 | 30 |
| LASSO | 0.02418861156716993 | 0.029111665118820556 | 30 |
| Ridge | 0.024210779534916217 | 0.029223377919418418 | 30 |

## 5. Validation metier des scenarios
| scenario_key | scenario | scenario_type | narrative | UNRATE_delta | GDP_delta | HY_SPREAD_delta | FEDFUNDS_delta | CPI_delta | severity_score | pd_lift_floor | economically_adverse |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| adverse | Adverse | macro | Ralentissement macroeconomique general avec hausse du chomage et spreads credit. | 2.5 | -2.5 | 2.0 | 1.0 | 1.0 | 0.332 | 1.597 | True |
| severe | Severe | macro | Scenario macro severe combinant contraction PIB, chomage eleve et tension credit. | 4.0 | -3.5 | 2.0 | 1.0 | 1.5 | 0.487 | 1.877 | True |
| rate_shock | Choc Taux | taux | Hausse brutale des taux et de l'inflation, pression forte sur LGD/EAD. | 1.0 | -1.5 | 3.0 | 3.0 | 3.0 | 0.266 | 1.479 | True |
| market_2018 | Choc Marche 2018 | marche | Stress marche modere centre sur les spreads credit, sans recession profonde. | -0.1 | 0.0 | 1.7999999999999998 | -0.1 | -0.1 | 0.024 | 1.043 | True |
| ukraine_2022 | Inflation Ukraine 2022 | geopolitique_inflation | Choc inflation/geopolitique: taux et prix eleves, tension credit sans choc chomage majeur. | -0.2999999999999998 | -0.1 | 2.2 | 1.5999999999999996 | 6.0 | 0.133 | 1.238 | True |
| crisis_2008 | Crise 2008 | historique | Rejeu de la crise financiere mondiale, scenario historique systemique. | 6.0 | -6.3 | 15.0 | -2.25 | -2.4 | 0.898 | 2.616 | True |
| covid_2020 | Crise COVID-19 | historique | Choc sanitaire extreme, rupture rapide activite/chomage et forte incertitude. | 10.7 | -11.0 | 5.300000000000001 | -2.25 | -1.8 | 1.173 | 3.112 | True |

## 6. Utilisation des donnees FRED
| variable | fred_series | frequency | role | business_use |
| --- | --- | --- | --- | --- |
| UNRATE | UNRATE | M | Predictor PD/stress | Chomage: hausse attendue de la PD |
| FEDFUNDS | FEDFUNDS | M | Predictor PD/LGD/EAD | Taux directeur: choc de taux et cout du credit |
| CPI | CPIAUCSL | M | Source CPI_change | Inflation annuelle |
| GDPC1 | GDPC1 | Q | Source GDPC1_growth | Cycle economique reel |
| GDPC1_growth | GDPC1 | Q->M | Predictor PD/stress | Contraction PIB: hausse attendue du risque |
| HY_SPREAD | BAMLH0A0HYM2 | D->M | Predictor PD/LGD | Tension marche credit high-yield |
| DRCCLACBS | DRCCLACBS | Q->M | Calibration target | Taux officiel de delinquence bancaire |

## 7. Resultats de stress ECL
| Scenario | ECL_stressed_M$ | ECL_baseline_M$ | ΔECL_M$ | ECL_lift | Coverage_% | PD_baseline_% | PD_stressed_% | PD_final_lift | PD_model_lift | PD_floor_lift | Severity_score | LGD_stressed_% | EAD_Mrd$ | Coherent_stress |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Adverse | 7764.06 | 3803.04 | 3961.03 | 2.04 | 22.83 | 45.27 | 83.22 | 2.087 | 2.087 | 1.597 | 0.332 | 66.25 | 35.19 | True |
| Severe | 8431.24 | 3803.04 | 4628.2 | 2.22 | 24.79 | 45.27 | 88.57 | 2.464 | 2.464 | 1.877 | 0.487 | 67.57 | 35.7 | True |
| Choc Taux | 8726.36 | 3803.04 | 4923.32 | 2.29 | 25.66 | 45.27 | 86.08 | 2.269 | 2.269 | 1.479 | 0.266 | 72.48 | 35.36 | True |
| Choc Marche 2018 | 4132.79 | 3803.04 | 329.75 | 1.09 | 12.15 | 45.27 | 48.33 | 1.068 | 1.068 | 1.043 | 0.024 | 60.39 | 34.0 | True |
| Inflation Ukraine 2022 | 6252.47 | 3803.04 | 2449.43 | 1.64 | 18.39 | 45.27 | 66.06 | 1.469 | 1.469 | 1.238 | 0.133 | 66.28 | 34.55 | True |
| Crise 2008 | 9589.22 | 3803.04 | 5786.18 | 2.52 | 28.2 | 45.27 | 93.37 | 3.106 | 3.106 | 2.616 | 0.898 | 73.34 | 36.04 | True |
| Crise COVID-19 | 10042.99 | 3803.04 | 6239.95 | 2.64 | 29.53 | 45.27 | 96.1 | 3.841 | 3.841 | 3.112 | 1.173 | 71.82 | 37.64 | True |

## 8. Controles automatiques de coherence
| Scenario | ECL_lift_ge_1 | Delta_ECL_non_negative | PD_stressed_ge_baseline | PD_lift_ge_floor | validation_status |
| --- | --- | --- | --- | --- | --- |
| Adverse | True | True | True | True | OK |
| Severe | True | True | True | True | OK |
| Choc Taux | True | True | True | True | OK |
| Choc Marche 2018 | True | True | True | True | OK |
| Inflation Ukraine 2022 | True | True | True | True | OK |
| Crise 2008 | True | True | True | True | OK |
| Crise COVID-19 | True | True | True | True | OK |

## 9. ECL forward-looking IFRS 9 (controle complementaire)
| scenario_key | Scenario | weight | ECL_M$ | weighted_ECL_M$ |
| --- | --- | --- | --- | --- |
| baseline | Baseline | 0.4 | 3803.0378761821767 | 1521.2151504728708 |
| adverse | Adverse | 0.35 | 7764.06 | 2717.421 |
| severe | Severe | 0.25 | 8431.24 | 2107.81 |
| forward_looking | ECL Forward-Looking | 1.0 | 6346.44615047287 | 6346.44615047287 |

## 10. Comparaison des moteurs de stress testing
Cette section compare des moteurs de stress concurrents: sensibilite deterministe, satellite macro, migration Markov, challenger ML et modele hybride. Le champion est retenu par scoring, pas par une ponderation forward-looking.
| model_name | ECL_stressed_M$ | ECL_lift | PD_baseline_% | PD_stressed_% | PD_lift | LGD_stressed_% | EAD_stressed_M$ | observed_DR_error | economic_coherent | backtesting_score | economic_score | temporal_stability_score | ecl_precision_score | interpretability_score | final_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| deterministic_sensitivity | 10508.377 | 2.4402 | 45.274 | 90.112 | 1.9904 | 73.34 | 36044.461 | 0.833419 | True | 0.0 | 1.0 | 0.85 | 0.0 | 0.95 | 0.5125 |
| markov_stage_migration | 13789.957 | 3.2023 | 45.274 | 90.112 | 1.9904 | 73.34 | 36044.461 | 0.833419 | True | 0.0 | 1.0 | 0.85 | 0.0 | 0.85 | 0.4975 |
| hybrid_satellite_markov_floor | 13789.957 | 3.2023 | 45.274 | 90.112 | 1.9904 | 73.34 | 36044.461 | 0.833419 | True | 0.0 | 1.0 | 0.85 | 0.0 | 0.8 | 0.49 |
| satellite_macro | 10508.377 | 2.4402 | 45.274 | 90.112 | 1.9904 | 73.34 | 36044.461 | 0.833419 | True | 0.0 | 1.0 | 0.85 | 0.0 | 0.7 | 0.475 |
| ml_macro_conditioned | 10408.858 | 2.4171 | 45.274 | 88.987 | 1.9655 | 73.34 | 36044.461 | 0.822166 | True | 0.0135022119726092 | 1.0 | 0.85 | 0.0135022119726092 | 0.55 | 0.4585759953876742 |

### Champion stress testing
| champion_model | scenario_name | selection_rule | observed_target_dr |
| --- | --- | --- | --- |
| deterministic_sensitivity | crisis_2008 | max final_score | 0.0677 |

## 11. Migration IFRS 9 Markov
| scenario | severity_score | S1_to_S2_% | S1_to_S3_% | S2_to_S3_% | S3_maintained_% | n_migrated |
| --- | --- | --- | --- | --- | --- | --- |
| adverse | 0.332 | 9.8 | 2.3 | 26.3 | 97.7 | 253375 |
| severe | 0.487 | 11.4 | 2.9 | 29.7 | 98.0 | 296205 |
| rate_shock | 0.266 | 9.2 | 2.1 | 24.8 | 97.5 | 235231 |
| market_2018 | 0.024 | 6.7 | 1.1 | 19.5 | 97.0 | 168584 |
| ukraine_2022 | 0.133 | 7.8 | 1.5 | 21.9 | 97.3 | 198486 |
| crisis_2008 | 0.898 | 15.5 | 4.6 | 38.8 | 98.8 | 409423 |
| covid_2020 | 1.173 | 18.2 | 5.7 | 44.8 | 99.3 | 485285 |

## 12. Resilience CET1
| Scenario | CET1_initial_% | ECL_baseline_M$ | ECL_stressed_M$ | ΔECL_M$ | ΔECL_net_M$ | ΔCET1_% | CET1_post_stress_% | RWA_M$ | Capital_initial_M$ | Capital_post_M$ | Shortfall_4_5_M$ | Shortfall_7_0_M$ | zone | color | management_action | is_critical |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Adverse | 12.0 | 3803.04 | 7764.06 | 3961.03 | 2772.72 | -8.15 | 3.85 | 34004.21 | 4080.51 | 1307.79 | 222.4 | 1072.51 | 🚨 Critique (CET1 < 4.5% — Bâle III) | red | Plan de recapitalisation: injection capital, cession actifs risques, reduction origination. | True |
| Severe | 12.0 | 3803.04 | 8431.24 | 4628.2 | 3239.74 | -9.53 | 2.47 | 34004.21 | 4080.51 | 840.76 | 689.43 | 1539.53 | 🚨 Critique (CET1 < 4.5% — Bâle III) | red | Plan de recapitalisation: injection capital, cession actifs risques, reduction origination. | True |
| Choc Taux | 12.0 | 3803.04 | 8726.36 | 4923.32 | 3446.33 | -10.14 | 1.86 | 34004.21 | 4080.51 | 634.18 | 896.01 | 1746.12 | 🚨 Critique (CET1 < 4.5% — Bâle III) | red | Plan de recapitalisation: injection capital, cession actifs risques, reduction origination. | True |
| Choc Marche 2018 | 12.0 | 3803.04 | 4132.79 | 329.75 | 230.83 | -0.68 | 11.32 | 34004.21 | 4080.51 | 3849.68 | 0.0 | 0.0 | ✓ Résilient (CET1 ≥ 7%) | green | Surveillance normale et maintien des coussins. | False |
| Inflation Ukraine 2022 | 12.0 | 3803.04 | 6252.47 | 2449.43 | 1714.6 | -5.04 | 6.96 | 34004.21 | 4080.51 | 2365.9 | 0.0 | 14.39 | ⚠ Attention (4.5% ≤ CET1 < 7%) | orange | Plan de conservation capital: limiter dividendes, reduire croissance RWA, renforcer recouvrement. | False |
| Crise 2008 | 12.0 | 3803.04 | 9589.22 | 5786.18 | 4050.33 | -11.91 | 0.09 | 34004.21 | 4080.51 | 30.18 | 1500.01 | 2350.12 | 🚨 Critique (CET1 < 4.5% — Bâle III) | red | Plan de recapitalisation: injection capital, cession actifs risques, reduction origination. | True |
| Crise COVID-19 | 12.0 | 3803.04 | 10042.99 | 6239.95 | 4367.97 | -12.85 | -0.85 | 34004.21 | 4080.51 | -287.46 | 1817.65 | 2667.76 | 💥 Rupture (CET1 < 0% — Défaillance) | darkred | Resolution/restructuration: recapitalisation urgente ou plan de resolution. | True |

## 13. Rapport DFAST-like
Rapport disponible: `outputs\results\dfast_like_report.md`

## Conclusion de validation
Le moteur est valide pour un prototype academique si les controles de stress sont OK, si le satellite champion respecte la coherence economique et si les resultats CET1 restent interpretes comme une approximation pedagogique.

## Limites restantes
- CET1 simplifie sauf integration d'un fichier FFIEC/capital reel.
- Les scenarios COVID-2020 et choc marche 2018 sont des tests historiques calibres FRED.
- Les resultats doivent etre figes apres execution sequentielle des notebooks.