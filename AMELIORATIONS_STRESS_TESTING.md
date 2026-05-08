# Ameliorations Stress Testing IFRS 9

Ce fichier resume les ameliorations ajoutees pour renforcer le projet sur la partie stress testing, modelisation et validation.

## 1. Nouveaux scenarios

Le moteur contient maintenant une structure plus complete :

- `baseline` : conditions normales ;
- `adverse` : choc macro modere ;
- `severe` : choc macro severe ;
- `rate_shock` : choc de taux ;
- `crisis_2008` : scenario historique 2008.

La fonction `validate_scenario_design()` produit un rapport metier :

- variation du chomage ;
- variation du PIB ;
- variation du spread ;
- score de severite ;
- lift PD minimal attendu ;
- controle de coherence adverse.

Sortie generee :

```text
outputs/results/scenario_design_validation.csv
```

## 2. Stress PD avec garde-fou economique

Avant, le modele satellite pouvait parfois donner une PD stressee plus faible que la PD baseline. C'etait difficile a defendre pour un scenario adverse.

Maintenant, la PD stressee combine :

```text
PD_lift_final = max(PD_lift_modele_satellite, PD_lift_plancher_metier)
```

Le plancher metier depend d'un score de severite macro :

- chomage en hausse ;
- PIB en baisse ;
- spread HY en hausse ;
- delinquance bancaire en hausse ;
- inflation/taux en hausse.

La fonction `compute_pd_stress_diagnostics()` explique pour chaque scenario :

- DR satellite baseline ;
- DR satellite stress ;
- lift modele ;
- lift plancher ;
- lift final.

## 3. LGD et EAD stressés plus coherents

La LGD stressee depend maintenant de :

```text
LGD_stressed = LGD_base x (1 + alpha x hausse_taux + beta x hausse_spread + gamma x hausse_chomage)
```

L'EAD stressee conserve une logique CCF :

```text
EAD_stressed = EAD_base x CCF_stressed
```

Avec CCF croissant sous hausse du chomage et des taux.

## 4. Validation automatique des sorties de stress

La fonction `validate_stress_outputs()` verifie que les sorties respectent la logique minimale :

- `ECL_lift >= 1` ;
- `Delta ECL >= 0` ;
- `PD_stressed >= PD_baseline` ;
- `PD_final_lift >= PD_floor_lift`.

Sortie generee :

```text
outputs/results/stress_validation_report.csv
```

## 5. Multi-modeles satellites

Le module `src/satellite_models.py` compare maintenant davantage de modeles :

- OLS ;
- Ridge ;
- LASSO ;
- ElasticNet ;
- RandomForestRegressor ;
- GradientBoostingRegressor ;
- XGBoostRegressor si XGBoost est installe ;
- Probit si possible.

Le champion satellite n'est plus choisi seulement par RMSE. Le choix privilegie les modeles qui respectent la coherence economique :

```text
DR(choc adverse) >= DR(baseline)
```

Puis le RMSE departage les modeles.

## 6. Backtesting walk-forward satellite

La fonction `satellite_walk_forward_validation()` teste la stabilite temporelle :

```text
Train passe -> prediction trimestre suivant
```

Elle sauvegarde :

```text
outputs/models/satellite_pd_walk_forward.csv
```

Cela donne une vraie validation hors temps des modeles satellites macro.

## 7. Migration IFRS 9 par matrice de Markov

En plus de la migration par seuils PD, le projet contient maintenant une matrice Markov :

```text
          S1      S2      S3
S1      92.5%    6.5%    1.0%
S2       5.0%   76.0%   19.0%
S3       0.0%    3.0%   97.0%
```

La matrice est stressee selon la severite macro :

- plus le scenario est severe, plus les migrations S1->S2/S3 et S2->S3 augmentent ;
- les prets les plus risqués migrent en premier ;
- le resultat est reproductible.

Fonctions :

```python
stressed_markov_matrix()
compute_markov_stage_migration()
```

Sortie du notebook avance :

```text
outputs/results/stage_migration_markov_summary.csv
```

## 8. ECL forward-looking ponderee

La fonction `compute_forward_looking_summary()` calcule :

```text
ECL_IFRS9 = 40% x ECL_baseline
          + 35% x ECL_adverse
          + 25% x ECL_severe
```

Sortie :

```text
outputs/results/forward_looking_ecl.csv
```

## 9. Nouveau notebook

Un notebook a ete ajoute :

```text
notebooks/07_Stress_Testing_Validation_Avancee.ipynb
```

Il execute les nouvelles briques :

1. validation des scenarios ;
2. entrainement multi-modeles satellites ;
3. backtesting walk-forward ;
4. stress ECL avec garde-fous ;
5. validation economique des sorties ;
6. migration Markov ;
7. ECL forward-looking.

## Formulation pour la soutenance

Tu peux dire :

> Le projet a ete renforce pour devenir un framework de stress testing IFRS 9 multi-modeles. Les scenarios sont controles metier, les modeles satellites sont compares non seulement par performance statistique mais aussi par coherence economique, et les sorties de stress sont validees automatiquement. Le moteur calcule ensuite PD, LGD et EAD stresses, l'ECL stressee, les migrations IFRS 9 par matrice Markov, l'ECL forward-looking ponderee et l'impact sur la resilience CET1.

## Limite restante

La validation COVID/Freddie Mac et le CET1 FFIEC reel restent des extensions possibles. La version actuelle est maintenant beaucoup plus solide pour un atelier IFRS 9/stress testing, mais pas encore un moteur reglementaire complet de production bancaire.
