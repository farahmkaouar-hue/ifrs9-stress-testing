"""
satellite_models.py — Modèles satellites macro → PD et macro → LGD.
Comparaison OLS / Ridge / LASSO / Probit avec métriques professionnelles.

Usage:
    from src.satellite_models import build_satellite_models, train_satellite_pd, train_satellite_lgd
"""

import numpy as np
import pandas as pd
import joblib
from pathlib import Path

import statsmodels.api as sm
from sklearn.linear_model import Ridge, Lasso, ElasticNet
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error
from sklearn.preprocessing import StandardScaler

try:
    import xgboost as xgb
    HAS_XGB_REG = True
except ImportError:
    HAS_XGB_REG = False

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "outputs" / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Variables macro candidates pour les modèles satellites
# Note : DRCCLACBS est utilisé comme CIBLE (variable dépendante calibrée),
#        donc exclu de la liste des prédicteurs pour éviter la circularité.
MACRO_PD_VARS  = ["UNRATE", "GDPC1_growth", "FEDFUNDS", "HY_SPREAD", "CPI_change"]
MACRO_LGD_VARS = ["FEDFUNDS", "HY_SPREAD", "UNRATE"]


# ---------------------------------------------------------------------------
# 1. Agrégation du taux de défaut trimestriel
# ---------------------------------------------------------------------------
def compute_quarterly_default_rate(
    df: pd.DataFrame,
    date_col: str = "issue_d",
    target_col: str = "default_flag",
) -> pd.DataFrame:
    """
    Agrège le taux de défaut par trimestre d'émission.
    Returns : DataFrame trimestriel avec DR_t, volume, LGD_mean.
    """
    df = df.copy()
    df["quarter"] = df[date_col].dt.to_period("Q")

    agg = df.groupby("quarter").agg(
        DR=("default_flag", "mean"),
        n_loans=("default_flag", "count"),
        LGD_mean=("LGD", "mean"),
        EAD_sum=("EAD", "sum"),
    ).reset_index()

    agg["quarter_ts"] = agg["quarter"].dt.to_timestamp()
    agg = agg.sort_values("quarter_ts")

    print(f"[compute_quarterly_default_rate] {len(agg)} trimestres — DR range: "
          f"{agg['DR'].min():.2%} → {agg['DR'].max():.2%}")
    return agg


# ---------------------------------------------------------------------------
# 2. Fusion données macro trimestrielles
# ---------------------------------------------------------------------------
def merge_macro_quarterly(
    dr_quarterly: pd.DataFrame,
    macro: pd.DataFrame,
) -> pd.DataFrame:
    """
    Fusionne le taux de défaut trimestriel avec les variables macro.

    Stratégie cible (DR) :
    ----------------------
    On utilise DRCCLACBS (taux de délinquance Fed, série FRED officielle) comme
    variable dépendante CALIBRÉE, en remplacement du DR par cohorte du portefeuille.

    Pourquoi ? Le DR par cohorte Lending Club souffre d'un biais de troncature sévère :
    - Les cohortes 2007-2010 montrent un DR élevé (loans arrivés à maturité, crise observée)
    - Les cohortes 2015-2018 paraissent peu risquées (prêts trop jeunes pour avoir défauté)
    Ce biais crée des coefficients inversés dans le satellite, rendant l'ECL stressée
    inférieure à l'ECL baseline (économiquement incohérent).

    DRCCLACBS = taux officiel Fed mesuré à un instant t (pas de troncature).
    Il est normalisé à l'échelle du portefeuille via un facteur de proportionnalité.
    """
    macro_q = macro.resample("QS").mean()
    macro_q.index = macro_q.index.to_period("Q")
    macro_q.index.name = "quarter"
    macro_reset = macro_q.reset_index()

    merged = dr_quarterly.merge(macro_reset, on="quarter", how="left")
    merged = merged.dropna(subset=["DR"])
    merged = merged.set_index("quarter_ts")

    # --- Calibration de la cible via DRCCLACBS ---
    if "DRCCLACBS" in merged.columns:
        # DRCCLACBS est en % → convertir en fraction
        drcclacbs_rate = merged["DRCCLACBS"] / 100.0
        # Facteur de mise à l'échelle : le portefeuille LC est plus risqué que
        # la moyenne bancaire US → on conserve le ratio relatif des deux séries
        portfolio_mean  = merged["DR"].mean()
        drcclacbs_mean  = drcclacbs_rate.mean()
        scale = portfolio_mean / drcclacbs_mean if drcclacbs_mean > 0 else 1.0
        merged["DR"] = (drcclacbs_rate * scale).clip(lower=0)
        print(f"  [merge_macro_quarterly] Cible DR recalibrée via DRCCLACBS "
              f"(facteur ×{scale:.2f}) → range {merged['DR'].min():.3f}-{merged['DR'].max():.3f}")
    else:
        print("  [merge_macro_quarterly] DRCCLACBS absent — cible DR par cohorte (biais possible)")

    avail = [v for v in MACRO_PD_VARS if v in merged.columns]
    print(f"[merge_macro_quarterly] {len(merged)} observations | "
          f"Prédicteurs disponibles : {avail}")
    return merged


# ---------------------------------------------------------------------------
# 3. Métriques des modèles satellites
# ---------------------------------------------------------------------------
def compute_satellite_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    model_sm=None,
    label: str = "model",
) -> dict:
    """
    Métriques professionnelles pour un modèle satellite régressif.

    Retourne : R², R² ajusté, RMSE, MAE, AIC, BIC, Durbin-Watson, note DW
    """
    from statsmodels.stats.stattools import durbin_watson

    n = len(y_true)
    resid = y_true - y_pred
    ss_res = np.sum(resid ** 2)
    ss_tot = np.sum((y_true - y_true.mean()) ** 2)
    # R² out-of-sample (sur validation) — peut être négatif si le modèle
    # fait pire que prédire la moyenne sur des données non vues
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

    # R²_adj calculé également sur la validation (cohérence avec R²)
    k_approx = len(MACRO_PD_VARS)
    r2_adj = 1 - (1 - r2) * (n - 1) / max(n - k_approx - 1, 1) if n > k_approx + 1 else r2

    aic, bic = np.nan, np.nan
    if model_sm is not None:
        try:
            aic = model_sm.aic
            bic = model_sm.bic
        except Exception:
            pass

    dw = float(durbin_watson(resid)) if len(resid) > 1 else np.nan
    dw_ok = "✓ OK" if 1.5 <= dw <= 2.5 else "✗ Problème autocorrélation"

    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mae  = mean_absolute_error(y_true, y_pred)

    return {
        "Model":  label,
        "R²":     round(r2, 4),
        "R²_adj": round(r2_adj, 4),
        "RMSE":   round(rmse, 4),
        "MAE":    round(mae, 4),
        "AIC":    round(aic, 1) if not np.isnan(aic) else np.nan,
        "BIC":    round(bic, 1) if not np.isnan(bic) else np.nan,
        "DW":     round(dw, 3),
        "DW_ok":  dw_ok,
    }


def compute_vif(X: pd.DataFrame) -> pd.Series:
    """Variance Inflation Factor pour détecter la multicolinéarité. VIF < 5 = OK."""
    from statsmodels.stats.outliers_influence import variance_inflation_factor
    X_vals = X.values
    vif = pd.Series(
        {X.columns[i]: variance_inflation_factor(X_vals, i) for i in range(X.shape[1])},
        name="VIF",
    )
    return vif


def predict_satellite_model(model, model_name: str, X: np.ndarray) -> np.ndarray:
    """Prediction generique pour statsmodels, modeles standardises et sklearn."""
    if model_name in ("OLS", "Probit"):
        return np.asarray(model.predict(sm.add_constant(X, has_constant="add")))
    if isinstance(model, tuple):
        estimator, scaler = model
        return np.asarray(estimator.predict(scaler.transform(X)))
    return np.asarray(model.predict(X))


def economic_sensitivity_check(
    model,
    model_name: str,
    macro_vars: list[str],
    baseline: dict | None = None,
    shock: dict | None = None,
) -> dict:
    """
    Controle si le modele reagit dans le bon sens a un scenario adverse.

    Attendu : DR(choc) >= DR(baseline).
    """
    baseline = baseline or {
        "UNRATE": 4.0, "GDPC1_growth": 2.0, "FEDFUNDS": 2.5,
        "HY_SPREAD": 3.5, "CPI_change": 2.0,
    }
    shock = shock or {
        "UNRATE": 8.0, "GDPC1_growth": -1.5, "FEDFUNDS": 3.5,
        "HY_SPREAD": 5.5, "CPI_change": 3.5,
    }
    x_base = np.array([[baseline.get(v, 0) for v in macro_vars]])
    x_shock = np.array([[shock.get(v, 0) for v in macro_vars]])
    dr_base = float(predict_satellite_model(model, model_name, x_base)[0])
    dr_shock = float(predict_satellite_model(model, model_name, x_shock)[0])
    return {
        "DR_base_check": round(max(dr_base, 0.0), 4),
        "DR_shock_check": round(max(dr_shock, 0.0), 4),
        "economic_ok": bool(dr_shock >= dr_base),
        "stress_lift_check": round(dr_shock / max(dr_base, 1e-6), 4),
    }


# ---------------------------------------------------------------------------
# 4. Modèles Satellites PD
# ---------------------------------------------------------------------------
def train_satellite_pd(
    data: pd.DataFrame,
    macro_vars: list[str] | None = None,
    val_start: str = "2015",
    save: bool = True,
) -> tuple[dict, pd.DataFrame]:
    """
    Entraîne et compare 4 modèles satellites PD :
    OLS | Ridge | LASSO | Probit

    Train : données avant val_start
    Val   : données à partir de val_start

    Returns
    -------
    trained : dict {nom: modèle/résultat statsmodels}
    results_df : DataFrame comparatif
    """
    if macro_vars is None:
        macro_vars = [v for v in MACRO_PD_VARS if v in data.columns]

    data_clean = data.dropna(subset=["DR"] + macro_vars)
    train = data_clean[data_clean.index < val_start]
    val   = data_clean[data_clean.index >= val_start]

    X_train = train[macro_vars].values
    y_train = train["DR"].values
    X_val   = val[macro_vars].values if len(val) > 0 else X_train[-4:]
    y_val   = val["DR"].values  if len(val) > 0 else y_train[-4:]

    # Normalisation pour Ridge/LASSO
    scaler = StandardScaler()
    X_train_sc = scaler.fit_transform(X_train)
    X_val_sc   = scaler.transform(X_val)

    X_train_sm = sm.add_constant(X_train)
    X_val_sm   = sm.add_constant(X_val)

    trained = {}
    results = []

    # --- OLS ---
    try:
        ols = sm.OLS(y_train, X_train_sm).fit()
        pred_val = ols.predict(X_val_sm)
        metrics = compute_satellite_metrics(y_val, pred_val, ols, "OLS")
        trained["OLS"] = ols
        results.append(metrics)
        print(f"  OLS      → R²_adj={metrics['R²_adj']:.4f} | RMSE={metrics['RMSE']:.4f} "
              f"| DW={metrics['DW']:.3f} {metrics['DW_ok']}")
    except Exception as e:
        print(f"  [WARN] OLS échoué : {e}")

    # --- Ridge ---
    try:
        ridge = Ridge(alpha=1.0)
        ridge.fit(X_train_sc, y_train)
        pred_val = ridge.predict(X_val_sc)
        metrics = compute_satellite_metrics(y_val, pred_val, label="Ridge")
        trained["Ridge"] = (ridge, scaler)
        results.append(metrics)
        print(f"  Ridge    → R²_adj={metrics['R²_adj']:.4f} | RMSE={metrics['RMSE']:.4f} "
              f"| DW={metrics['DW']:.3f}")
    except Exception as e:
        print(f"  [WARN] Ridge échoué : {e}")

    # --- LASSO ---
    try:
        lasso = Lasso(alpha=0.001, max_iter=10_000)
        lasso.fit(X_train_sc, y_train)
        pred_val = lasso.predict(X_val_sc)
        metrics = compute_satellite_metrics(y_val, pred_val, label="LASSO")
        trained["LASSO"] = (lasso, scaler)
        results.append(metrics)
        nonzero = (lasso.coef_ != 0).sum()
        print(f"  LASSO    → R²_adj={metrics['R²_adj']:.4f} | RMSE={metrics['RMSE']:.4f} "
              f"| {nonzero}/{len(macro_vars)} vars sélectionnées")
    except Exception as e:
        print(f"  [WARN] LASSO échoué : {e}")

    # --- ElasticNet ---
    try:
        enet = ElasticNet(alpha=0.001, l1_ratio=0.5, max_iter=10_000)
        enet.fit(X_train_sc, y_train)
        pred_val = enet.predict(X_val_sc)
        metrics = compute_satellite_metrics(y_val, pred_val, label="ElasticNet")
        trained["ElasticNet"] = (enet, scaler)
        results.append(metrics)
        print(f"  ElasticNet -> RMSE={metrics['RMSE']:.4f}")
    except Exception as e:
        print(f"  [WARN] ElasticNet failed: {e}")

    # --- RandomForestRegressor ---
    try:
        rf = RandomForestRegressor(
            n_estimators=300, max_depth=4, min_samples_leaf=3, random_state=42
        )
        rf.fit(X_train, y_train)
        pred_val = rf.predict(X_val)
        metrics = compute_satellite_metrics(y_val, pred_val, label="RandomForestReg")
        trained["RandomForestReg"] = rf
        results.append(metrics)
        print(f"  RF-Reg   -> RMSE={metrics['RMSE']:.4f}")
    except Exception as e:
        print(f"  [WARN] RandomForestReg failed: {e}")

    # --- GradientBoostingRegressor ---
    try:
        gbr = GradientBoostingRegressor(
            n_estimators=150, max_depth=2, learning_rate=0.05, random_state=42
        )
        gbr.fit(X_train, y_train)
        pred_val = gbr.predict(X_val)
        metrics = compute_satellite_metrics(y_val, pred_val, label="GradientBoostingReg")
        trained["GradientBoostingReg"] = gbr
        results.append(metrics)
        print(f"  GB-Reg   -> RMSE={metrics['RMSE']:.4f}")
    except Exception as e:
        print(f"  [WARN] GradientBoostingReg failed: {e}")

    # --- XGBoostRegressor ---
    if HAS_XGB_REG:
        try:
            xgbr = xgb.XGBRegressor(
                n_estimators=200,
                max_depth=2,
                learning_rate=0.05,
                subsample=0.9,
                colsample_bytree=0.9,
                objective="reg:squarederror",
                random_state=42,
                n_jobs=-1,
            )
            xgbr.fit(X_train, y_train)
            pred_val = xgbr.predict(X_val)
            metrics = compute_satellite_metrics(y_val, pred_val, label="XGBoostReg")
            trained["XGBoostReg"] = xgbr
            results.append(metrics)
            print(f"  XGB-Reg  -> RMSE={metrics['RMSE']:.4f}")
        except Exception as e:
            print(f"  [WARN] XGBoostReg failed: {e}")

    # --- Probit ---
    try:
        # DR normalisé entre 0+ε et 1-ε pour Probit
        y_train_clip = np.clip(y_train, 1e-6, 1 - 1e-6)
        probit = sm.Probit(y_train_clip, X_train_sm).fit(disp=False)
        pred_val = probit.predict(X_val_sm)
        metrics = compute_satellite_metrics(y_val, pred_val, probit, "Probit")
        trained["Probit"] = probit
        results.append(metrics)
        print(f"  Probit   → R²_adj={metrics['R²_adj']:.4f} | RMSE={metrics['RMSE']:.4f} "
              f"| DW={metrics['DW']:.3f}")
    except Exception as e:
        print(f"  [WARN] Probit échoué : {e}")

    results_df = pd.DataFrame(results).set_index("Model")

    econ_rows = {}
    for model_name, model in trained.items():
        try:
            econ_rows[model_name] = economic_sensitivity_check(model, model_name, macro_vars)
        except Exception:
            econ_rows[model_name] = {
                "DR_base_check": np.nan,
                "DR_shock_check": np.nan,
                "economic_ok": False,
                "stress_lift_check": np.nan,
            }
    econ_df = pd.DataFrame.from_dict(econ_rows, orient="index")
    results_df = results_df.join(econ_df)

    # Champion : priorite a la coherence economique, puis RMSE.
    eligible = results_df[results_df["economic_ok"] == True]
    if len(eligible) == 0:
        eligible = results_df
    dw_ok_models = eligible[eligible["DW"].between(1.5, 2.5)]
    champion_pool = dw_ok_models if len(dw_ok_models) > 0 else eligible
    champion_name = champion_pool["RMSE"].idxmin()
    print(f"\n✓ Modèle satellite PD champion : {champion_name} "
          f"(RMSE={results_df.loc[champion_name, 'RMSE']:.4f})")

    if save:
        joblib.dump(trained, MODELS_DIR / "satellite_pd_models.pkl")
        results_df.to_csv(MODELS_DIR / "satellite_pd_comparison.csv")
        joblib.dump(macro_vars, MODELS_DIR / "satellite_pd_features.pkl")

    return trained, results_df


# ---------------------------------------------------------------------------
# 5. Modèles Satellites LGD
# ---------------------------------------------------------------------------
def train_satellite_lgd(
    data: pd.DataFrame,
    macro_vars: list[str] | None = None,
    val_start: str = "2015",
    save: bool = True,
) -> tuple[dict, pd.DataFrame]:
    """
    Entraîne 3 modèles satellites LGD : OLS | Ridge | LASSO.
    Même protocole que PD mais sur LGD_mean comme variable cible.
    """
    if macro_vars is None:
        macro_vars = [v for v in MACRO_LGD_VARS if v in data.columns]

    data_clean = data.dropna(subset=["LGD_mean"] + macro_vars)
    if len(data_clean) < 10:
        print("[WARN] Pas assez de données LGD pour le satellite")
        return {}, pd.DataFrame()

    train = data_clean[data_clean.index < val_start]
    val   = data_clean[data_clean.index >= val_start]

    X_train = train[macro_vars].values
    y_train = train["LGD_mean"].values
    X_val   = val[macro_vars].values  if len(val) > 0 else X_train[-4:]
    y_val   = val["LGD_mean"].values  if len(val) > 0 else y_train[-4:]

    scaler = StandardScaler()
    X_train_sc = scaler.fit_transform(X_train)
    X_val_sc   = scaler.transform(X_val)
    X_train_sm = sm.add_constant(X_train)
    X_val_sm   = sm.add_constant(X_val)

    trained = {}
    results = []

    for model_name, m_obj in [
        ("OLS",   lambda: sm.OLS(y_train, X_train_sm).fit()),
        ("Ridge", lambda: (Ridge(alpha=1.0).fit(X_train_sc, y_train), scaler)),
        ("LASSO", lambda: (Lasso(alpha=0.001, max_iter=5000).fit(X_train_sc, y_train), scaler)),
    ]:
        try:
            model = m_obj()
            if isinstance(model, tuple):
                m, sc = model
                pred_val = m.predict(sc.transform(X_val))
                metrics = compute_satellite_metrics(y_val, pred_val, label=model_name)
                trained[model_name] = model
            else:
                pred_val = model.predict(X_val_sm)
                metrics = compute_satellite_metrics(y_val, pred_val, model, model_name)
                trained[model_name] = model
            results.append(metrics)
            print(f"  {model_name:6s} LGD → R²={metrics['R²']:.4f} | RMSE={metrics['RMSE']:.4f}")
        except Exception as e:
            print(f"  [WARN] {model_name} LGD échoué : {e}")

    results_df = pd.DataFrame(results).set_index("Model") if results else pd.DataFrame()

    if save and len(results) > 0:
        joblib.dump(trained, MODELS_DIR / "satellite_lgd_models.pkl")
        results_df.to_csv(MODELS_DIR / "satellite_lgd_comparison.csv")
        joblib.dump(macro_vars, MODELS_DIR / "satellite_lgd_features.pkl")

    return trained, results_df


# ---------------------------------------------------------------------------
# 6. Prédiction avec modèle satellite champion
# ---------------------------------------------------------------------------
def predict_pd_satellite(
    macro_scenario: dict,
    champion_name: str = "OLS",
    trained_models: dict | None = None,
    macro_vars: list[str] | None = None,
) -> float:
    """
    Prédit le taux de défaut agrégé pour un scénario macro donné.

    Parameters
    ----------
    macro_scenario : dict {variable: valeur stressée}
        Ex: {'UNRATE': 10.0, 'GDPC1_growth': -4.3, 'FEDFUNDS': 0.25, ...}
    champion_name : str
        Nom du modèle champion satellite
    trained_models : dict (si None, charge depuis disque)
    macro_vars : list des variables dans le bon ordre

    Returns
    -------
    DR_stressed : float — taux de défaut prédit sous le scénario
    """
    if trained_models is None:
        trained_models = joblib.load(MODELS_DIR / "satellite_pd_models.pkl")
    if macro_vars is None:
        macro_vars = joblib.load(MODELS_DIR / "satellite_pd_features.pkl")

    model = trained_models[champion_name]
    X_stress = np.array([[macro_scenario.get(v, 0) for v in macro_vars]])

    dr = float(predict_satellite_model(model, champion_name, X_stress)[0])

    return max(dr, 0.0)  # PD ne peut pas être négative


def predict_lgd_satellite(
    macro_scenario: dict,
    champion_name: str = "OLS",
    trained_models: dict | None = None,
    macro_vars: list[str] | None = None,
) -> float:
    """Prédit la LGD agrégée pour un scénario macro donné."""
    if trained_models is None:
        trained_models = joblib.load(MODELS_DIR / "satellite_lgd_models.pkl")
    if macro_vars is None:
        macro_vars = joblib.load(MODELS_DIR / "satellite_lgd_features.pkl")

    model = trained_models.get(champion_name)
    if model is None:
        return 0.45  # fallback

    X_stress = np.array([[macro_scenario.get(v, 0) for v in macro_vars]])

    if champion_name == "OLS":
        X_sm = sm.add_constant(X_stress, has_constant="add")
        lgd = float(model.predict(X_sm)[0])
    else:
        m, scaler = model
        lgd = float(m.predict(scaler.transform(X_stress))[0])

    return float(np.clip(lgd, 0.0, 1.0))


# ---------------------------------------------------------------------------
# 7. Calibration sur la crise 2008
# ---------------------------------------------------------------------------
def calibrate_2008(
    data: pd.DataFrame,
    champion_model,
    champion_name: str,
    macro_vars: list[str],
) -> dict:
    """
    Vérifie que le modèle satellite reproduit le pic de défaut 2008-2009.
    Returns dict avec les valeurs observées et prédites sur 2008Q1-2010Q4.
    """
    crisis = data.loc["2007":"2010"].copy()
    if len(crisis) == 0:
        return {}

    observed_peak = crisis["DR"].max()
    peak_date = crisis["DR"].idxmax()

    # Prédiction sur la crise
    X_crisis = crisis[macro_vars].values
    if champion_name in ("OLS", "Probit"):
        X_sm = sm.add_constant(X_crisis, has_constant="add")
        predicted = champion_model.predict(X_sm)
    else:
        m, sc = champion_model
        predicted = m.predict(sc.transform(X_crisis))

    predicted_peak = max(predicted)

    print(f"\n=== Calibration Crise 2008-2009 ===")
    print(f"  Taux de défaut observé max  : {observed_peak:.2%} ({peak_date})")
    print(f"  Taux de défaut prédit max   : {predicted_peak:.2%}")
    print(f"  Écart                       : {abs(observed_peak - predicted_peak):.2%}")

    target = 0.12  # ~12% mentionné dans la présentation
    if observed_peak < target:
        print(f"  [INFO] Le dataset montre {observed_peak:.2%} de défauts max "
              "(les prêts émis en 2009 n'ont peut-être pas tous défailli avant 2018)")

    return {
        "observed_peak": observed_peak,
        "predicted_peak": predicted_peak,
        "error": abs(observed_peak - predicted_peak),
        "crisis_df": pd.DataFrame({
            "DR_observed":  crisis["DR"].values,
            "DR_predicted": predicted,
        }, index=crisis.index),
    }


def satellite_walk_forward_validation(
    data: pd.DataFrame,
    macro_vars: list[str] | None = None,
    min_train_quarters: int = 16,
    save: bool = True,
) -> pd.DataFrame:
    """
    Validation walk-forward du satellite PD.

    A chaque date, on entraine OLS/Ridge/LASSO/ElasticNet sur le passe et on
    predit le trimestre suivant. Les resultats servent de backtesting temporel.
    """
    if macro_vars is None:
        macro_vars = [v for v in MACRO_PD_VARS if v in data.columns]

    data_clean = data.dropna(subset=["DR"] + macro_vars).sort_index()
    rows = []
    for split_idx in range(min_train_quarters, len(data_clean) - 1):
        train = data_clean.iloc[:split_idx]
        test = data_clean.iloc[[split_idx]]
        X_train, y_train = train[macro_vars].values, train["DR"].values
        X_test, y_test = test[macro_vars].values, test["DR"].values

        scaler = StandardScaler()
        X_train_sc = scaler.fit_transform(X_train)
        X_test_sc = scaler.transform(X_test)
        candidates = {
            "OLS": sm.OLS(y_train, sm.add_constant(X_train)).fit(),
            "Ridge": (Ridge(alpha=1.0).fit(X_train_sc, y_train), scaler),
            "LASSO": (Lasso(alpha=0.001, max_iter=10_000).fit(X_train_sc, y_train), scaler),
            "ElasticNet": (ElasticNet(alpha=0.001, l1_ratio=0.5, max_iter=10_000).fit(X_train_sc, y_train), scaler),
        }
        for name, model in candidates.items():
            pred = float(predict_satellite_model(model, name, X_test)[0])
            rows.append({
                "test_date": test.index[0],
                "Model": name,
                "DR_observed": float(y_test[0]),
                "DR_predicted": max(pred, 0.0),
                "abs_error": abs(float(y_test[0]) - max(pred, 0.0)),
            })

    wf = pd.DataFrame(rows)
    if len(wf) > 0:
        summary = wf.groupby("Model").agg(
            MAE=("abs_error", "mean"),
            RMSE=("abs_error", lambda x: float(np.sqrt(np.mean(np.square(x))))),
            n_folds=("abs_error", "count"),
        ).reset_index()
        wf = wf.merge(summary, on="Model", suffixes=("", "_model"))
    if save:
        wf.to_csv(MODELS_DIR / "satellite_pd_walk_forward.csv", index=False)
    return wf
