# Explication detaillee des notebooks du projet Far7ti

Ce document explique les notebooks cellule par cellule. Pour chaque cellule importante, on resume :
- ce qu'elle fait ;
- pourquoi elle le fait ;
- l'interet de la methode ;
- les resultats obtenus et leur interpretation.

Note importante : certaines sorties visibles dans les notebooks ne sont pas parfaitement coherentes entre executions. Par exemple, `03_Baseline_ECL.ipynb` affiche une ECL baseline de 770.71 M$, alors que `06_Resilience_Reverse_Stress.ipynb` recharge un fichier `ecl_baseline.parquet` qui donne 201.24 M$. Cela indique probablement que les notebooks ont ete executes a des moments differents, avec des versions differentes du modele ou des fichiers de sortie. Pour une soutenance, il faut idealement reexecuter les notebooks dans l'ordre 01 -> 06 pour harmoniser les chiffres.

---

## Notebook 01 - EDA : Exploration des donnees

### Cellule 1 - Markdown d'introduction
Elle presente l'objectif : explorer le dataset Lending Club et les variables macro pour comprendre le risque de credit avant toute modelisation.
L'interet est de justifier les choix de preprocessing et de modelisation au lieu de construire le modele "a l'aveugle".

### Cellule 2 - Imports et chemins
Elle importe `numpy`, `pandas`, `matplotlib`, `seaborn`, configure les figures et definit les dossiers `data` et `outputs`.
Pourquoi : standardiser l'environnement d'analyse et permettre la sauvegarde automatique des graphiques.
Resultat : `Imports OK`.

### Cellule 3 - Titre section chargement
Elle annonce le chargement des donnees.

### Cellule 4 - Chargement portefeuille et macro
Elle appelle `load_loan_data()` et `load_macro_data()`.
Pourquoi cette methode : `loan.csv` est volumineux, donc `load_loan_data` lit par chunks et conserve seulement les colonnes utiles, ce qui economise la RAM.
Resultats : 2 260 668 prets, 31 colonnes chargees, 315 points macro mensuels, environ 758 Mo en memoire.
Interpretation : le portefeuille est assez grand pour entrainer des modeles robustes, mais il impose des choix techniques sobres en memoire.

### Cellule 5 - Titre vue d'ensemble
Elle introduit la description globale du portefeuille.

### Cellule 6 - Types et apercu
Elle affiche les types des colonnes, le nombre de lignes/colonnes et les premieres lignes.
Pourquoi : verifier que les colonnes sont correctement lues et identifier les variables textuelles/numeriques.
Resultats : 16 colonnes `float64`, 12 colonnes texte, 3 colonnes entieres.
Interpretation : beaucoup de variables doivent etre transformees avant modelisation, notamment les dates, categories et taux.

### Cellule 7 - Distribution des statuts et creation `default_flag`
Elle visualise `loan_status`, puis transforme certains statuts en defaut (`Default`, `Charged Off`, etc.).
Pourquoi : le modele PD a besoin d'une cible binaire.
Interet : cette definition rapproche le dataset d'une logique risque de credit IFRS 9.
Resultat : taux de defaut global 11.61 %, soit 262 447 prets.
Interpretation : la classe defaut est minoritaire ; il faudra traiter le desequilibre dans le modele.

### Cellule 8 - Montants et durees
Elle trace la distribution de `loan_amnt` et la repartition 36/60 mois.
Pourquoi : comprendre l'exposition et la maturite des prets.
Resultats : montant moyen 15 047 $, median 12 900 $, maximum 40 000 $.
Interpretation : la distribution est asymetrique ; l'exposition moyenne reste moderee, mais les gros prets peuvent peser fortement dans l'ECL.

### Cellule 9 - Titre valeurs manquantes
Elle introduit l'analyse des NaN.

### Cellule 10 - Analyse des valeurs manquantes
Elle calcule le taux de NaN par colonne et trace un graphique avec seuils 5 % et 40 %.
Pourquoi : decider entre imputation et suppression.
Interet : eviter de supprimer des variables utiles ou d'introduire un biais par mauvaise imputation.
Resultats : `emp_length` 6.5 %, `last_pymnt_d`, `revol_util`, `dti` environ 0.1 %, aucune colonne au-dessus de 40 %.
Interpretation : pas besoin de supprimer de colonnes principales ; une imputation simple suffit.

### Cellule 11 - Titre analyse par segment
Elle annonce l'analyse du risque par categories.

### Cellule 12 - Taux de defaut par grade
Elle groupe les prets par `grade` et calcule taux de defaut et volume.
Pourquoi : verifier que le grade Lending Club est bien ordonne en risque.
Resultats : A 3.18 %, B 7.71 %, C 12.83 %, D 18.39 %, E 26.19 %, F 34.35 %, G 37.43 %.
Interpretation : gradient tres clair A -> G ; `grade` est une variable explicative majeure de PD.

### Cellule 13 - Heatmap par sub-grade
Elle calcule le taux de defaut pour A1...G5.
Pourquoi : observer une granularite plus fine que le grade.
Interet : le `sub_grade` capture un ordre de risque plus precis.
Resultat : graphique heatmap.
Interpretation : on attend une hausse progressive de A1 vers G5 ; si elle est visible, cela valide l'encodage ordinal.

### Cellule 14 - Defaut par duree, logement et objet du pret
Elle compare les taux de defaut selon `term`, `home_ownership` et `purpose`.
Pourquoi : ces variables refletent le profil emprunteur et le type de besoin.
Interet : detecter des segments naturellement plus risqués.
Interpretation : les prets longs, certains objets de pret et certains statuts de logement peuvent porter plus de risque.

### Cellule 15 - Titre analyse temporelle
Elle introduit la dynamique 2007-2018.

### Cellule 16 - Taux de defaut par annee
Elle parse `issue_d`, cree `year` et `quarter`, puis trace le taux de defaut annuel.
Pourquoi : le credit risk est cyclique et depend de la conjoncture.
Resultats : 2007 26.20 %, 2008 20.73 %, 2009 13.69 %, puis baisse jusqu'a 1.40 % en 2018.
Interpretation : les cohortes anciennes ont eu plus de temps pour faire defaut ; les annees recentes sont probablement tronquees. C'est une limite importante.

### Cellule 17 - Titre distributions continues
Elle annonce l'etude des variables numeriques.

### Cellule 18 - Distributions `int_rate`, `dti`, `annual_inc`, `revol_util`
Elle trace un violin plot du taux d'interet par grade, l'histogramme du DTI, du revenu log-transforme et de l'utilisation revolving.
Pourquoi : detecter asymetrie, outliers et relations avec le risque.
Interet : justifier le clipping du DTI/revol_util et la transformation log du revenu.
Interpretation : les variables sont non gaussiennes ; des transformations robustes sont preferable a une hypothese de normalite.

### Cellule 19 - Titre correlations
Elle introduit la matrice de correlation.

### Cellule 20 - Correlations avec `default_flag`
Elle encode `grade` numeriquement et calcule les correlations Pearson.
Resultats : correlations absolues principales avec le defaut : `grade_num` 0.221, `int_rate` 0.196, `revol_util` 0.067, `dti` 0.034.
Interpretation : le risque est surtout porte par le grade et le taux ; les correlations lineaires restent modestes, donc des modeles non lineaires peuvent etre utiles.

### Cellule 21 - Titre variables macro
Elle introduit le lien macro-credit.

### Cellule 22 - Defaut trimestriel vs macro
Elle trace le taux de defaut trimestriel avec `UNRATE`, la croissance du PIB reel, les Fed Funds et les spreads HY.
Pourquoi : verifier visuellement si le portefeuille reagit au cycle macroeconomique.
Interet : preparer les modeles satellites macro -> PD.
Resultat : graphique multi-panneaux.
Interpretation : le chomage, le PIB et les spreads sont des drivers economiquement pertinents du stress credit.

### Cellule 23 - Titre LGD
Elle introduit l'analyse preliminary de la LGD.

### Cellule 24 - LGD empirique
Elle calcule la recovery rate sur les prets en defaut, puis `LGD = 1 - recovery_rate`.
Pourquoi : IFRS 9 exige PD x LGD x EAD ; il faut donc une estimation de la perte en cas de defaut.
Interet : partir des recouvrements observes plutot qu'une LGD fixe arbitraire.
Resultats : 262 447 prets defaillants, LGD mediane 66.65 %, moyenne 62.51 %. Par grade : A 52.43 %, G 75.72 %.
Interpretation : la LGD augmente avec le risque du grade, ce qui est coherent.

### Cellule 25 - Conclusion EDA
Elle resume les observations et les decisions : clipping, imputation, encodage ordinal, parsing dates, gestion du desequilibre.
Interpretation : cette cellule fait le pont vers le preprocessing.

---

## Notebook 02 - Preprocessing

### Cellule 1 - Introduction
Elle presente l'objectif : transformer le brut en `outputs/loan_clean.parquet`.

### Cellule 2 - Imports et chemins
Elle prepare les librairies, styles graphiques et dossiers.
Resultat : `Imports OK`.

### Cellule 3 - Description du pipeline
Elle liste les etapes : chargement chunked, parsing, encodage, feature engineering, outliers, imputation, targets, LGD/EAD, fusion macro.
Interet : documenter un pipeline reproductible.

### Cellule 4 - Execution `build_clean_dataset`
Elle lance le pipeline complet.
Pourquoi cette methode : centraliser le nettoyage dans `src/data_prep.py` evite de dupliquer du code entre notebooks.
Resultats : dataset final 2 260 668 lignes x 55 colonnes, defaut 11.61 %, stages `{1: 1972587, 3: 262447, 2: 25634}`, LGD mediane 58.96 %, EAD total 10.05 Md$.
Interpretation : le portefeuille est majoritairement sain en nombre et surtout en EAD.

### Cellule 5 - Titre validation
Elle introduit les controles qualite du dataset final.

### Cellule 6 - Structure, cible, NaN, types
Elle verifie dimensions, desequilibre, NaN dans les features PD et types.
Resultats : 2 260 668 lignes, 55 colonnes en memoire, 1 998 221 sains contre 262 447 defauts, seulement 4 NaN sur `log_annual_inc`.
Interpretation : dataset globalement propre ; les 4 NaN restants doivent etre traites par `fillna(0)` dans les modeles.

### Cellule 7 - Statistiques descriptives
Elle affiche `describe()` sur les features PD.
Pourquoi : verifier les ordres de grandeur apres transformation.
Interpretation : on controle que les caps et encodages n'ont pas cree de valeurs aberrantes majeures.

### Cellule 8 - Titre staging IFRS 9
Elle introduit la distribution des stages.

### Cellule 9 - Distribution des stages et EAD par stage
Elle compte Stage 1/2/3 et calcule l'EAD.
Resultats : Stage 1 87.26 %, Stage 2 1.13 %, Stage 3 11.61 %. EAD total 10.05 Md$, Stage 1 = 97.1 % de l'EAD.
Interpretation : les defauts sont nombreux en count mais tres faibles en EAD residuelle, car beaucoup de prets defaillants ont un capital restant tres faible.

### Cellule 10 - Titre LGD/EAD
Elle introduit la validation des composantes ECL.

### Cellule 11 - LGD par grade et distribution EAD
Elle verifie la monotonie de la LGD par grade et trace `log(EAD)`.
Resultats : LGD moyenne A 52.43 %, B 56.12 %, C 61.27 %, D 64.94 %, E 68.84 %, F 72.28 %, G 75.72 %. Monotonie OK.
Interpretation : la LGD proxy par grade est coherente economiquement.

### Cellule 12 - Titre sauvegarde
Elle annonce la verification du fichier Parquet.

### Cellule 13 - Verification `loan_clean.parquet`
Elle recharge le fichier sauvegarde et affiche colonnes et apercu.
Resultats : fichier de 40.8 Mo, 2 260 668 lignes, 28 colonnes sauvegardees.
Interet : sauvegarder seulement les colonnes utiles reduit le stockage et accelere les notebooks suivants.

### Cellule 14 - Resume final
Elle confirme les chiffres cles et indique le prochain notebook.

---

## Notebook 03 - Baseline ECL IFRS 9

### Cellule 1 - Introduction
Elle annonce la comparaison des modeles PD et le calcul ECL baseline.

### Cellule 2 - Imports
Elle prepare l'environnement.
Resultat : `Imports OK`.

### Cellule 3 - Titre chargement
Elle introduit le chargement du dataset nettoye.

### Cellule 4 - Chargement Parquet, downcast et split temporel
Elle lit uniquement les colonnes necessaires, downcast les types pour reduire la RAM, cree les features et split train/validation/test par date.
Pourquoi split temporel : en risque de credit, on evite d'entrainer sur le futur pour predire le passe.
Resultats : dataset 2 260 668 x 27, RAM 0.26 Go, 20 features PD, train 887 440, validation 877 986, test 495 242, defaut train 17.18 %, `scale_pos_weight` 4.8.
Interpretation : le train contient plus de defauts car les cohortes anciennes sont plus matures.

### Cellule 5 - Titre entrainement modeles
Elle annonce l'entrainement PD.

### Cellule 6 - Entrainement LogReg, RandomForest, XGBoost
Elle appelle `train_pd_models`.
Methodes :
- Logistic Regression : interpretable, baseline lineaire.
- Random Forest : capture non-linearites et interactions.
- XGBoost : boosting puissant pour donnees tabulaires.
- LightGBM serait utilise si installe.
Resultats : LogReg AUC 0.6661, RandomForest AUC 0.6924, XGBoost AUC 0.6830. Champion : RandomForest.
Interpretation : performances proches du seuil 0.70 ; modele acceptable mais pas excellent.

### Cellule 7 - Titre metriques
Elle introduit le tableau comparatif.

### Cellule 8 - Tableau metriques
Elle affiche AUC, Gini, KS, Brier, PSI, LogLoss.
Pourquoi ces metriques : AUC/Gini/KS mesurent la discrimination ; Brier/LogLoss la calibration ; PSI la stabilite.
Resultats : RandomForest meilleur globalement avec AUC 0.6924, Gini 0.3848, KS 0.2894, Brier 0.2081, PSI 0.0708.
Interpretation : PSI OK (<0.10), discrimination legerement sous les seuils usuels AUC 0.70 / Gini 0.40.

### Cellule 9 - Graphiques de comparaison
Elle visualise discrimination et calibration.
Interet : rendre le choix du champion lisible.

### Cellule 10 - Titre ROC
Elle annonce les courbes ROC.

### Cellule 11 - ROC et KS
Elle trace les ROC des modeles et le KS du champion.
Pourquoi : la ROC montre le compromis faux positifs/vrais positifs ; le KS montre la separation maximale.
Interpretation : RandomForest separe le mieux les defauts des non-defauts, mais la marge reste moderee.

### Cellule 12 - Titre walk-forward
Elle introduit la validation temporelle.

### Cellule 13 - Walk-forward validation
Elle reentraine annee par annee et teste sur l'annee suivante.
Pourquoi : tester la stabilite temporelle du modele.
Resultats : AUC moyen 0.6831, min 0.6554 en 2012, max 0.6986.
Interpretation : le modele est relativement stable mais reste sous 0.70 dans plusieurs annees.

### Cellule 14 - Titre SHAP
Elle introduit l'interpretabilite.

### Cellule 15 - SHAP values
Elle calcule SHAP sur 5 000 prets et produit beeswarm/bar plot.
Pourquoi SHAP : expliquer les contributions des variables pour un modele non lineaire.
Interet : utile pour gouvernance modele et interpretation risque.
Resultat : graphes SHAP generes, mais warning sur le dependence plot UNRATE.
Interpretation : l'importance globale est exploitable, mais le plot de dependance UNRATE a echoue a cause d'un probleme de dimension.

### Cellule 16 - Titre calcul ECL
Elle introduit la formule IFRS 9.

### Cellule 17 - Calcul ECL baseline
Elle applique `ECL = PD x LGD x EAD`, avec facteur horizon : Stage 1 = 12 mois / duree du pret ; Stage 2/3 = lifetime.
Pourquoi : IFRS 9 distingue pertes attendues 12 mois et lifetime.
Resultats affiches : ECL totale 770.71 M$, EAD 10.05 Md$, coverage 7.67 %, PD moyenne 45.27 %, LGD mediane 58.96 %.
Interpretation : PD moyenne tres elevee, probablement liee au class balancing/calibration ; a surveiller.

### Cellule 18 - Visualisation ECL baseline
Elle montre ECL par grade, distribution PD, ECL par stage et coverage par grade.
Resultats : ECL par grade A 73.66 M$, B 173.11 M$, C 264.77 M$, D 165.61 M$, E 66.47 M$, F 19.73 M$, G 7.36 M$.
Interpretation : les grades C/D concentrent l'ECL car ils combinent volume important et risque significatif.

### Cellule 19 - Cellule vide
Elle ne fait rien.

---

## Notebook 04 - Modeles satellites macro

### Cellule 1 - Introduction
Elle presente l'objectif : relier les variables macro au taux de defaut et a la LGD.

### Cellule 2 - Imports
Elle importe `statsmodels` et prepare les dossiers.

### Cellule 3 - Titre chargement/agregation
Elle introduit les donnees trimestrielles.

### Cellule 4 - Chargement minimal, aggregation trimestrielle, fusion macro
Elle lit seulement `default_flag`, `issue_d`, `LGD`, `EAD`, calcule un taux de defaut trimestriel, puis fusionne les series macro.
Pourquoi trimestriel : les variables macro comme PIB sont souvent trimestrielles.
Resultats : 47 trimestres, DR range 0.03 % -> 29.56 %, dataset trimestriel 47 x 14.
Interpretation : peu d'observations pour beaucoup de variables ; risque de surapprentissage et autocorrelation.

### Cellule 5 - Visualisation DR trimestriel
Elle trace le taux de defaut trimestriel 2007-2018.
Resultats : DR max 29.56 % en 2007-10-01, min 0.03 %.
Interpretation : la serie est fortement affectee par les cohortes et la maturite des prets.

### Cellule 6 - Titre VIF
Elle introduit la multicolinearite.

### Cellule 7 - VIF et correlation macro
Elle calcule le Variance Inflation Factor.
Pourquoi : eviter d'interpreter des coefficients instables quand les variables macro sont correlees.
Resultats : DRCCLACBS 35.55, UNRATE 34.24, HY_SPREAD 16.07, FEDFUNDS 4.45, CPI 4.18, GDPC1 3.37.
Interpretation : forte multicolinearite sur certaines variables ; Ridge est pertinent car il regularise.

### Cellule 8 - Titre entrainement satellites PD
Elle annonce les modeles OLS/Ridge/LASSO/Probit.

### Cellule 9 - Entrainement satellites PD
Elle entraine les regressions macro -> DR, train 2007-2014, validation 2015-2018.
Pourquoi ces methodes :
- OLS : interpretable.
- Ridge : robuste a la multicolinearite.
- LASSO : selection de variables.
- Probit : adapte a une probabilite, mais ici la cible continue pose probleme.
Resultats : OLS RMSE 0.1161, Ridge RMSE 0.1141, LASSO RMSE 0.1141, Probit echoue. Champion Ridge.
Interpretation : performances faibles, autocorrelation forte ; Ridge gagne legerement par RMSE.

### Cellule 10 - Tableau satellites
Elle affiche R2, R2 ajuste, RMSE, MAE, AIC/BIC, Durbin-Watson.
Resultats : DW 0.022 pour les modeles, donc autocorrelation severe.
Interpretation : les erreurs sont tres dependantes dans le temps ; un modele avec lags/ARIMA pourrait etre meilleur.

### Cellule 11 - Visualisation metriques satellites
Elle compare R2 ajuste, RMSE et DW.
Interet : visualiser que le champion par RMSE n'est pas forcement satisfaisant statistiquement.

### Cellule 12 - Titre coefficients
Elle introduit l'interpretation OLS.

### Cellule 13 - Coefficients OLS
Elle affiche le summary OLS et les coefficients avec intervalles.
Resultats : R2 0.570, R2 ajuste 0.463, AIC -132.5, DW 1.399 dans le summary OLS.
Interpretation : certains coefficients sont significatifs, mais l'echantillon est petit et la colinearite limite l'interpretation causale.

### Cellule 14 - Titre calibration 2008
Elle introduit le test historique.

### Cellule 15 - Calibration crise 2008
Elle compare DR observe et predit sur la crise.
Resultats : DR observe max 29.56 %, predit max 21.52 %, ecart 8.05 %.
Interpretation : le satellite sous-estime le pic de crise.

### Cellule 16 - Graphe calibration
Elle trace observe vs predit pendant 2007-2010.
Interet : montrer visuellement l'erreur de calibration en periode de stress.

### Cellule 17 - Titre satellites LGD
Elle introduit la modelisation LGD macro.

### Cellule 18 - Modeles satellites LGD
Elle entraine OLS/Ridge/LASSO sur `LGD_mean`.
Resultats : OLS RMSE 0.0080, Ridge 0.0082, LASSO 0.0110, DW tres faible.
Interpretation : LGD moyenne trimestrielle varie peu ; le RMSE est bas, mais le pouvoir explicatif est faible.

### Cellule 19 - Titre ponderation IFRS 9
Elle introduit la logique forward-looking.

### Cellule 20 - Prediction par scenario et ponderation
Elle predit un DR par scenario puis calcule un DR forward-looking pondere 40/35/25.
Resultats : baseline 21.48 %, choc macro 15.30 %, choc taux 22.72 %, crise 2008 10.50 %, forward-looking 16.57 %, lift 0.77.
Interpretation : certains scenarios adverses donnent un DR plus bas que baseline, ce qui est economiquement incoherent et montre une limite du satellite. Le code de stress corrige ensuite cela avec un plancher de lift a 1.0.

### Cellule 21 - Cellule vide
Elle ne fait rien.

---

## Notebook 05 - Stress Testing

### Cellule 1 - Introduction
Elle presente les trois scenarios : choc macro, choc taux, crise 2008.

### Cellule 2 - Imports
Elle charge librairies, `joblib`, chemins.

### Cellule 3 - Titre chargement
Elle annonce le chargement des modeles et donnees.

### Cellule 4 - Chargement dataset, ECL baseline, modeles PD et satellites
Elle recharge `loan_clean.parquet`, `ecl_baseline.parquet`, le modele PD champion et le satellite champion.
Resultats : PD champion `randomforest`, satellite champion `Ridge`, ECL baseline 770.71 M$.
Interpretation : le stress part de l'ECL baseline calculee dans le notebook 03.

### Cellule 5 - Titre scenarios
Elle introduit l'application des chocs.

### Cellule 6 - Calcul ECL stressee
Elle appelle `compute_stress_ecl`.
Methode : PD stressee = PD individuelle x lift macro ; LGD stressee augmente avec Fed Funds et HY spread ; EAD stressee augmente avec chomage et taux.
Resultats dans ce notebook : Choc Macro 622.32 M$ (x0.81), Choc Taux 1 025.47 M$ (x1.33), Crise 2008 396.71 M$ (x0.51).
Interpretation : le fait que Macro et 2008 baissent l'ECL est incoherent pour un stress adverse ; cela vient probablement d'un ancien modele satellite ou d'une execution non alignee avec le code actuel qui impose un lift minimum de 1.0.

### Cellule 7 - Titre comparaison ECL
Elle annonce la comparaison baseline/stress.

### Cellule 8 - Graphique ECL et lift
Elle trace l'ECL par scenario et le ratio versus baseline.
Interet : lire immediatement quel scenario augmente le plus les pertes.
Interpretation : dans les sorties actuelles du notebook, le choc taux domine.

### Cellule 9 - Decomposition PD/LGD/EAD
Elle compare baseline et stress pour PD moyenne, LGD moyenne et EAD total.
Pourquoi : comprendre quelle composante explique la variation d'ECL.
Interpretation : l'ECL peut augmenter par hausse de PD, LGD ou EAD ; ici le choc taux augmente fortement LGD et PD.

### Cellule 10 - Titre ECL par grade
Elle introduit l'analyse par qualite de credit.

### Cellule 11 - ECL stressee par grade
Elle compare baseline et stress par grade A-G.
Interet : identifier les segments qui consomment le plus de provisions.
Interpretation : les grades intermediaires peuvent dominer en montant total a cause du volume, meme si les grades F/G sont plus risqués individuellement.

### Cellule 12 - Titre migration stage
Elle introduit les migrations IFRS 9.

### Cellule 13 - Migration de stage
Elle applique des seuils : Stage 1 -> 2 si la PD double ; Stage 2 -> 3 si PD stressee > 30 %.
Resultats : Macro Stage 2 -> 3 = 77.8 % ; Taux = 94.7 % ; Crise 2008 = 30.3 %. Stage 1 -> 2 = 0 % dans les trois cas.
Interpretation : la migration est concentree sur les prets deja Stage 2 ; le seuil de doublement ne deplace pas les Stage 1, probablement car le lift ou les PD ne franchissent pas le critere.

### Cellule 14 - Heatmaps de migration
Elle visualise les matrices de transition.
Interet : lecture rapide du passage entre stages.

### Cellule 15 - Distribution stage baseline vs crise 2008
Elle compare les proportions de stages avant/apres stress 2008.
Resultat : rappel migration 2008, Stage 2 -> 3 = 30.3 %.
Interpretation : le scenario 2008 degrade une partie des actifs deja fragiles.

---

## Notebook 06 - Resilience bancaire et Reverse Stress Test

### Cellule 1 - Introduction
Elle presente le lien stress -> capital CET1.
Formule : `CET1_post = CET1_initial - DeltaECL x (1 - tax_rate) / RWA`.
Pourquoi : transformer l'impact comptable ECL en impact prudentiel capital.

### Cellule 2 - Imports et constantes CET1
Elle importe les fonctions de resilience et affiche les seuils.
Resultats : CET1 initial 12 %, seuil Bale III 4.5 %.

### Cellule 3 - Titre chargement
Elle annonce le chargement.

### Cellule 4 - Chargement donnees/modeles/resultats
Elle recharge le portefeuille, l'ECL baseline, les modeles et le resume stress.
Resultats : ECL baseline 201.24 M$, EAD/RWA 10 051.59 M$, CET1 12 %.
Interpretation : attention, cette ECL baseline differe du notebook 03 ; il faut harmoniser les sorties.

### Cellule 5 - Titre impact CET1
Elle introduit le tableau CET1 par scenario.

### Cellule 6 - Recalcul stress et CET1
Elle recalcule les ECL stressees, puis applique `compute_cet1_table`.
Resultats : Choc Macro ECL 483.33 M$, CET1 10.04 % ; Choc Taux ECL 567.11 M$, CET1 9.45 % ; Crise 2008 ECL 642.93 M$, CET1 8.92 %. Tous restent au-dessus de 7 %.
Interpretation : meme le scenario le plus severe ne franchit pas le seuil reglementaire.

### Cellule 7 - Visualisation CET1
Elle trace CET1 post-stress et Delta ECL par scenario.
Interet : lecture directe de la zone verte/orange/rouge.
Interpretation : les trois scenarios sont classes resilients.

### Cellule 8 - Titre courbe de resilience
Elle introduit la courbe intensite du choc -> CET1.

### Cellule 9 - Calcul courbe de resilience
Elle calcule 25 points entre baseline et 2.5 fois le scenario 2008.
Pourquoi : ne pas tester seulement trois points, mais toute une plage d'intensite.
Resultat : `resilience_curve.csv` sauvegarde.

### Cellule 10 - Plot courbe resilience
Elle trace CET1 et ECL stressee en fonction de l'intensite.
Resultat : le CET1 reste > 4.5 % sur toute la plage testee.
Interpretation : le portefeuille est tres resilient dans les hypotheses actuelles.

### Cellule 11 - Titre reverse stress
Elle annonce la recherche du point de rupture.

### Cellule 12 - Reverse stress test
Elle utilise une recherche binaire sur l'intensite du choc pour atteindre CET1 = 4.5 %.
Pourquoi cette methode : la bisection est efficace quand on cherche un seuil sur une fonction monotone.
Resultat : meme a 3 fois le scenario 2008, le CET1 reste au-dessus du seuil.
Interpretation : aucun point de rupture trouve dans la plage testee.

### Cellule 13 - Visualisation point de rupture
Elle ne trace quelque chose que si `intensity_critical` existe.
Resultat : pas de graphique de rupture car aucun point critique n'a ete trouve.

### Cellule 14 - Titre rapport final
Elle introduit la synthese.

### Cellule 15 - Rapport final resilience
Elle affiche le tableau de resilience.
Resultats : CET1 post-stress 10.04 %, 9.45 %, 8.92 % ; tous resilients.
Interpretation : la banque conserve un coussin au-dessus de 7 %.

### Cellule 16 - Dashboard final
Elle cree une synthese visuelle : ECL, CET1, coverage ratio, courbe de resilience.
Interet : produire une vue finale exploitable pour presentation.
Resultat : dashboard final genere.

---

## Conclusion generale

Le projet suit une chaine IFRS 9 complete :
1. exploration du risque et des variables macro ;
2. nettoyage et construction des variables PD/LGD/EAD/stage ;
3. entrainement du modele PD et calcul ECL baseline ;
4. construction des modeles satellites macro ;
5. application des scenarios de stress ;
6. traduction en impact CET1 et reverse stress test.

Points forts :
- pipeline clair et modulaire dans `src/` ;
- traitement memoire adapte a un gros fichier ;
- logique IFRS 9 complete PD x LGD x EAD ;
- analyse de resilience CET1 bien presentee.

Points a surveiller :
- incoherence entre ECL baseline 770.71 M$ et 201.24 M$ selon les notebooks ;
- modeles satellites faibles/autocorreles ;
- certains scenarios macro donnent parfois une baisse de DR/ECL, ce qui doit etre corrige ou explique ;
- SHAP dependence plot echoue pour UNRATE ;
- reexecuter tous les notebooks dans l'ordre avant de figer les chiffres du rapport.
