"""
ecl_engine.py — Modélisation PD (4 modèles), métriques professionnelles,
SHAP values et calcul ECL baseline IFRS 9.

Usage:
    from src.ecl_engine import train_pd_models, evaluate_models, compute_ecl_baseline
"""

import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.metrics import (
    roc_auc_score, brier_score_loss, log_loss, roc_curve
)
from sklearn.tree import DecisionTreeClassifier
from scipy.stats import ks_2samp

try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False
    print("[WARN] xgboost non installé")

try:
    import lightgbm as lgb
    HAS_LGB = True
except ImportError:
    HAS_LGB = False
    print("[WARN] lightgbm non installé")

try:
    import shap
    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False
    print("[WARN] shap non installé")

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "outputs" / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# 1. Construction des modèles PD
# ---------------------------------------------------------------------------
def build_pd_models(scale_pos_weight: float = 13.0) -> dict:
    """
    Retourne un dict {nom: modèle_sklearn} des 4 modèles à comparer.

    Parameters
    ----------
    scale_pos_weight : float
        Ratio négatifs/positifs ≈ 93/7 ≈ 13 pour gérer le déséquilibre
    """
    models = {
        "LogReg": LogisticRegression(
            class_weight="balanced",
            max_iter=1000,
            solver="lbfgs",
            C=0.1,
            random_state=42,
        ),
        "RandomForest": RandomForestClassifier(
            n_estimators=200,
            class_weight="balanced",
            max_depth=8,
            min_samples_leaf=50,
            n_jobs=-1,
            random_state=42,
        ),
    }

    if HAS_XGB:
        models["XGBoost"] = xgb.XGBClassifier(
            scale_pos_weight=scale_pos_weight,
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            eval_metric="auc",
            use_label_encoder=False,
            tree_method="hist",
            n_jobs=-1,
            random_state=42,
        )

    if HAS_LGB:
        models["LightGBM"] = lgb.LGBMClassifier(
            is_unbalance=True,
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            num_leaves=63,
            n_jobs=-1,
            random_state=42,
            verbose=-1,
        )

    return models


# ---------------------------------------------------------------------------
# 2. Métriques professionnelles du risque de crédit
# ---------------------------------------------------------------------------
def compute_psi(expected: np.ndarray, actual: np.ndarray, n_bins: int = 10) -> float:
    """PSI — Population Stability Index."""
    breakpoints = np.percentile(expected, np.linspace(0, 100, n_bins + 1))
    breakpoints = np.unique(breakpoints)
    if len(breakpoints) < 2:
        return 0.0

    def _pct(arr):
        counts, _ = np.histogram(arr, bins=breakpoints)
        pct = counts / max(len(arr), 1)
        return np.where(pct == 0, 1e-6, pct)

    e = _pct(expected)
    a = _pct(actual)
    return float(np.sum((a - e) * np.log(a / e)))


def evaluate_model(
    model,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    model_name: str = "model",
) -> dict:
    """
    Calcule les 6 métriques professionnelles de credit risk pour un modèle.

    Métriques retournées
    --------------------
    AUC-ROC   : Discrimination globale (> 0.70 requis)
    Gini      : 2*AUC - 1 (> 0.40 standard Bâle II)
    KS        : max(TPR - FPR) — séparation défauts/non-défauts (> 0.30)
    Brier     : MSE probabilités (< 0.10)
    PSI       : Stabilité population train→test (< 0.10)
    LogLoss   : Calibration globale (minimiser)
    """
    y_prob_train = model.predict_proba(X_train)[:, 1]
    y_prob_test  = model.predict_proba(X_test)[:, 1]

    auc   = roc_auc_score(y_test, y_prob_test)
    gini  = 2 * auc - 1
    ks    = ks_2samp(y_prob_test[y_test == 1], y_prob_test[y_test == 0]).statistic
    brier = brier_score_loss(y_test, y_prob_test)
    psi   = compute_psi(y_prob_train, y_prob_test)
    ll    = log_loss(y_test, y_prob_test)

    result = {
        "Model":   model_name,
        "AUC-ROC": round(auc, 4),
        "Gini":    round(gini, 4),
        "KS":      round(ks, 4),
        "Brier":   round(brier, 4),
        "PSI":     round(psi, 4),
        "LogLoss": round(ll, 4),
    }
    return result


# ---------------------------------------------------------------------------
# 3. Entraînement et comparaison multi-modèles
# ---------------------------------------------------------------------------
def train_pd_models(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    save: bool = True,
) -> tuple[dict, pd.DataFrame]:
    """
    Entraîne les 4 modèles PD et retourne :
    - trained_models : dict {nom: modèle_fitté}
    - results_df     : DataFrame comparatif des métriques

    Le modèle champion est sélectionné sur AUC (test set).
    """
    models_def = build_pd_models()
    trained_models = {}
    results = []

    try:
        from sklearn.calibration import CalibratedClassifierCV
        _has_calibration = True
    except ImportError:
        _has_calibration = False

    for name, model in models_def.items():
        print(f"\n→ Entraînement {name}...")
        model.fit(X_train, y_train)

        # Calibration isotonique : ramène les probabilités prédites vers
        # le taux de défaut réel (évite la surestimation due à class_weight).
        # On calibre sur le val set pour ne pas toucher au test set.
        if _has_calibration:
            try:
                calibrated = CalibratedClassifierCV(model, cv="prefit", method="isotonic")
                calibrated.fit(X_val, y_val)
                trained_models[name] = calibrated
                print(f"  Calibration isotonique appliquée")
            except Exception as e:
                print(f"  [WARN] Calibration échouée ({e}) — modèle non calibré conservé")
                trained_models[name] = model
        else:
            trained_models[name] = model

        metrics = evaluate_model(trained_models[name], X_train, y_train, X_test, y_test, name)
        results.append(metrics)

        print(f"  AUC={metrics['AUC-ROC']:.4f} | Gini={metrics['Gini']:.4f} "
              f"| KS={metrics['KS']:.4f} | Brier={metrics['Brier']:.4f} "
              f"| PSI={metrics['PSI']:.4f}")

    results_df = pd.DataFrame(results).set_index("Model")

    # Sélection du champion sur AUC test
    champion_name = results_df["AUC-ROC"].idxmax()
    print(f"\n✓ Modèle champion : {champion_name} (AUC={results_df.loc[champion_name, 'AUC-ROC']:.4f})")

    if save:
        for name, model in trained_models.items():
            joblib.dump(model, MODELS_DIR / f"pd_model_{name.lower()}.pkl")
        results_df.to_csv(MODELS_DIR / "pd_model_comparison.csv")
        print(f"  Modèles sauvegardés dans {MODELS_DIR}")

    return trained_models, results_df


# ---------------------------------------------------------------------------
# 4. Walk-forward validation
# ---------------------------------------------------------------------------
def walk_forward_validation(
    df: pd.DataFrame,
    features: list[str],
    target: str = "default_flag",
    date_col: str = "issue_d",
    train_start: str = "2007-01-01",
    step_years: int = 1,
) -> pd.DataFrame:
    """
    Re-entraîne XGBoost (ou LogReg si XGBoost absent) à chaque année
    et évalue sur l'année suivante.

    Returns : DataFrame avec AUC par fold
    """
    model_cls = HAS_XGB
    results = []

    years = sorted(df[date_col].dt.year.dropna().unique())
    # Garde les années de 2010 à max-1 pour avoir assez de train
    test_years = [y for y in years if y >= 2011]

    for test_year in test_years:
        train_mask = (df[date_col].dt.year < test_year) & (df[date_col].dt.year >= 2007)
        test_mask  = df[date_col].dt.year == test_year

        X_tr, y_tr = df.loc[train_mask, features].fillna(0), df.loc[train_mask, target]
        X_te, y_te = df.loc[test_mask,  features].fillna(0), df.loc[test_mask,  target]

        if len(y_te) < 100 or y_te.sum() < 10:
            continue

        if HAS_XGB:
            m = xgb.XGBClassifier(
                scale_pos_weight=(y_tr == 0).sum() / max((y_tr == 1).sum(), 1),
                n_estimators=200, max_depth=5, learning_rate=0.05,
                tree_method="hist", n_jobs=-1, random_state=42,
                eval_metric="auc", use_label_encoder=False,
            )
        else:
            m = LogisticRegression(class_weight="balanced", max_iter=500, C=0.1)

        m.fit(X_tr, y_tr)
        auc = roc_auc_score(y_te, m.predict_proba(X_te)[:, 1])

        results.append({
            "test_year": test_year,
            "train_size": len(y_tr),
            "test_size":  len(y_te),
            "AUC": round(auc, 4),
        })
        print(f"  [{test_year}] Train={len(y_tr):,} | Test={len(y_te):,} | AUC={auc:.4f}")

    return pd.DataFrame(results)


# ---------------------------------------------------------------------------
# 5. SHAP Values
# ---------------------------------------------------------------------------
def compute_shap_values(model, X_sample: pd.DataFrame, model_name: str = "champion") -> dict:
    """
    Calcule les SHAP values pour le modèle champion.
    Retourne un dict avec shap_values et explainer.
    """
    if not HAS_SHAP:
        print("[WARN] shap non disponible")
        return {}

    print(f"Calcul des SHAP values pour {model_name}...")
    model_type = type(model).__name__

    if isinstance(
        model,
        (
            RandomForestClassifier,
            ExtraTreesClassifier,
            DecisionTreeClassifier,
        ),
    ) or "XGB" in model_type or "LGBM" in model_type or "LightGBM" in model_type or hasattr(model, "estimators_"):
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_sample)
        if isinstance(shap_values, list):
            shap_values = shap_values[1]  # classe positive
    else:
        explainer = shap.LinearExplainer(model, X_sample)
        shap_values = explainer.shap_values(X_sample)
        if isinstance(shap_values, list):
            shap_values = shap_values[1]

    return {"explainer": explainer, "shap_values": shap_values, "X_sample": X_sample}


# ---------------------------------------------------------------------------
# 6. Calcul ECL Baseline
# ---------------------------------------------------------------------------
def compute_ecl_baseline(
    df: pd.DataFrame,
    champion_model,
    features: list[str],
    chunk_size: int = 200_000,
) -> pd.DataFrame:
    """
    Calcule l'ECL baseline IFRS 9 = PD × LGD × EAD.

    Stage 1 : ECL 12 mois  → PD × LGD × EAD × (12 / term_months)
    Stage 2/3 : ECL lifetime → PD × LGD × EAD (horizon plein)

    Returns : df enrichi de PD_pred, ECL_12m, ECL_lifetime, ECL_ifrs9
    """
    result = df.copy(deep=False)

    # Prédiction PD en chunks pour limiter la pression mémoire sur les gros portefeuilles
    pd_pred = np.empty(len(df), dtype=np.float32)
    for start in range(0, len(df), chunk_size):
        stop = min(start + chunk_size, len(df))
        X_chunk = df.iloc[start:stop][features].fillna(0)
        pd_pred[start:stop] = champion_model.predict_proba(X_chunk)[:, 1]

    result["PD_pred"] = pd_pred

    # Horizon ECL selon le stage IFRS 9
    # Stage 1 → 12 mois / durée totale (fraction de l'année)
    term_months = df["term_months"].fillna(36) if "term_months" in df.columns else pd.Series(36, index=df.index)
    horizon_factor = np.where(
        result["stage"] == 1,
        12.0 / term_months.clip(1),
        1.0,
    )

    result["ECL_ifrs9"] = result["PD_pred"] * result["LGD"] * result["EAD"] * horizon_factor

    # Agrégations
    ecl_total = result["ECL_ifrs9"].sum()
    ead_total  = result["EAD"].sum()

    print(f"\n=== ECL Baseline IFRS 9 ===")
    print(f"ECL Total     : ${ecl_total / 1e6:,.2f} M")
    print(f"EAD Total     : ${ead_total / 1e9:,.2f} Mrd")
    print(f"Coverage Ratio: {ecl_total / ead_total:.2%}")
    print(f"PD Moyenne    : {result['PD_pred'].mean():.2%}")
    print(f"LGD Médiane   : {result['LGD'].median():.2%}")

    print("\nECL par Stage :")
    ecl_stage = result.groupby("stage").agg(
        ECL_M=("ECL_ifrs9", lambda x: x.sum() / 1e6),
        EAD_M=("EAD", lambda x: x.sum() / 1e6),
        PD_moy=("PD_pred", "mean"),
        LGD_moy=("LGD", "mean"),
        nb_prets=("ECL_ifrs9", "count"),
    )
    ecl_stage["Coverage"] = ecl_stage["ECL_M"] / ecl_stage["EAD_M"]
    print(ecl_stage.round(4).to_string())

    print("\nECL par Grade (A → G) :")
    if "grade" in result.columns:
        ecl_grade = result.groupby("grade")["ECL_ifrs9"].sum() / 1e6
        ecl_grade = ecl_grade.reindex(["A","B","C","D","E","F","G"])
        print(ecl_grade.round(2).to_string())

    return result


# ---------------------------------------------------------------------------
# 7. Utilitaires de chargement
# ---------------------------------------------------------------------------
def load_champion_model(model_name: str = "xgboost") -> object:
    """Charge un modèle PD sérialisé depuis outputs/models/."""
    path = MODELS_DIR / f"pd_model_{model_name}.pkl"
    if not path.exists():
        raise FileNotFoundError(f"Modèle introuvable : {path}")
    return joblib.load(path)


def get_roc_data(models: dict, X_test: pd.DataFrame, y_test: pd.Series) -> dict:
    """
    Retourne les données ROC (fpr, tpr, auc) pour chaque modèle.
    Utilisé pour tracer les courbes ROC superposées dans le notebook.
    """
    roc_data = {}
    for name, model in models.items():
        y_prob = model.predict_proba(X_test)[:, 1]
        fpr, tpr, _ = roc_curve(y_test, y_prob)
        auc = roc_auc_score(y_test, y_prob)
        roc_data[name] = {"fpr": fpr, "tpr": tpr, "auc": auc}
    return roc_data
