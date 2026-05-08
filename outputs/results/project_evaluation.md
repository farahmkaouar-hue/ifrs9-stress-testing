# Evaluation expert du projet IFRS 9 stress testing

**Score global: 90.0/100**
**Couverture livrables: 100.0/100**
**Penalites maturite: -10.0 points**

**Avis expert: Excellent prototype academique, proche d'un dossier soutenable.**

## Scores par pilier
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

## Penalites de maturite
| risk | points | action |
| --- | --- | --- |
| Capital/RWA encore pedagogique | 5 | Remplacer ou justifier les hypotheses CET1 avec donnees banque si disponibles. |
| Validation externe limitee | 3 | Ajouter benchmark externe ou stress historique supplementaire si le temps le permet. |
| Notebooks a reexecuter apres les derniers changements | 2 | Reexecuter 01 a 07 avant soutenance pour figer les sorties finales. |

## Forces principales
- Architecture complete: EDA, preprocessing, PD baseline, satellites macro, stress, CET1, validation et app.
- Stress testing traite comme une famille de moteurs concurrents, pas comme un simple calcul forward-looking.
- Scenarios historiques ajoutes: COVID-19, marche 2018 et crise 2008.
- Utilisation FRED documentee par variable, role et usage metier.

## Ameliorations prioritaires restantes
- Ajouter un vrai fichier capital/RWA banque si disponible pour remplacer les hypotheses CET1 simplifiees.
- Reexecuter tous les notebooks apres chaque modification majeure pour figer les outputs.
- Installer pyarrow et streamlit dans l'environnement applicatif pour lancer le dashboard.
- Documenter dans le memoire que le modele champion stress testing est retenu par score multi-criteres.

## Conclusion
Le projet est coherent pour une soutenance PFA: il explique les donnees, controle la qualite, construit l'ECL baseline, transforme les scenarios macro en chocs de pertes, compare plusieurs moteurs de stress et presente un diagnostic de resilience capital.