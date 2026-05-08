# Check-up final bancaire et modelisation

**Decision de soutenance : GO avec reserves explicites**

## Synthese des statuts
| OK | WATCH |
| --- | --- |
| 9 | 5 |

## Controles detailles
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

## Points a annoncer clairement
- Les resultats sont solides pour un prototype academique de stress testing IFRS 9.
- Le portefeuille Lending Club est plus risque qu'un portefeuille bancaire prime; les PD moyennes doivent etre interpretees dans ce contexte.
- Les hypotheses CET1/RWA sont pedagogiques sauf integration d'un fichier capital banque.
- Les modeles satellites macro sont surtout utilises comme mecanisme forward-looking et de sensibilite economique; une production bancaire exigerait plus d'historique et une validation externe.
- Le choix du champion stress testing est documente par scoring multi-criteres, ce qui renforce la gouvernance modele.

## Priorites finales
1. Refaire l'environnement Python portable avant demonstration.
2. Reexecuter les notebooks 01 a 07 pour figer les outputs finaux.
3. Presenter la calibration PD/CET1 comme limite methodologique et non comme erreur.