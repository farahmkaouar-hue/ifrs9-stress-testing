"""
data_prep.py — Chargement, nettoyage et préparation du dataset Lending Club
pour le moteur de stress testing IFRS 9.

Usage:
    from src.data_prep import load_loan_data, load_macro_data, build_clean_dataset
    df, macro = build_clean_dataset()
"""

import os
import numpy as np
import pandas as pd
from pathlib import Path

# ---------------------------------------------------------------------------
# Chemins
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
MACRO_DIR = DATA_DIR / "varmacro"
OUTPUT_DIR = ROOT / "outputs"

# Colonnes à conserver dès la lecture (économise ~80% de RAM sur 1.2 Go)
LOAN_COLS = [
    "loan_amnt", "funded_amnt", "term", "int_rate", "installment", "purpose",
    "grade", "sub_grade", "annual_inc", "dti", "home_ownership", "emp_length",
    "verification_status", "earliest_cr_line", "delinq_2yrs", "pub_rec",
    "open_acc", "revol_bal", "revol_util", "total_acc",
    "loan_status", "issue_d", "last_pymnt_d",
    "out_prncp", "total_rec_prncp", "total_pymnt", "recoveries",
    "collection_recovery_fee", "hardship_flag", "acc_now_delinq",
    "chargeoff_within_12_mths",
]

# Mapping loan_status → stage IFRS 9
STAGE_MAP = {
    "Current": 1,
    "In Grace Period": 1,
    "Fully Paid": 1,
    "Late (16-30 days)": 2,
    "Late (31-120 days)": 2,
    "Default": 3,
    "Charged Off": 3,
    "Does not meet the credit policy. Status:Charged Off": 3,
    "Does not meet the credit policy. Status:Fully Paid": 1,
}

GRADE_MAP = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7}

EMP_MAP = {
    "< 1 year": 0, "1 year": 1, "2 years": 2, "3 years": 3,
    "4 years": 4, "5 years": 5, "6 years": 6, "7 years": 7,
    "8 years": 8, "9 years": 9, "10+ years": 10,
}

VERIF_MAP = {"Not Verified": 0, "Source Verified": 1, "Verified": 2}

DEFAULT_STATUS = {"Default", "Charged Off",
                  "Does not meet the credit policy. Status:Charged Off"}

EXPECTED_SCHEMA = {
    "loan_amnt": "numeric",
    "funded_amnt": "numeric",
    "term": "object",
    "int_rate": "rate",
    "grade": "category",
    "sub_grade": "category",
    "annual_inc": "numeric",
    "dti": "numeric",
    "loan_status": "category",
    "issue_d": "date",
}

# Variables connues uniquement apres l'octroi. Elles sont utiles pour LGD/EAD
# historiques, mais ne doivent pas entrer dans un modele PD a l'octroi.
POST_ORIGINATION_COLS = {
    "last_pymnt_d", "out_prncp", "total_rec_prncp", "total_pymnt",
    "recoveries", "collection_recovery_fee", "loan_status",
}

PREPROCESSING_REPORTS_DIR = OUTPUT_DIR / "results"

FRED_VARIABLE_DICTIONARY = [
    {"variable": "UNRATE", "fred_series": "UNRATE", "frequency": "M", "role": "Predictor PD/stress", "business_use": "Chomage: hausse attendue de la PD"},
    {"variable": "FEDFUNDS", "fred_series": "FEDFUNDS", "frequency": "M", "role": "Predictor PD/LGD/EAD", "business_use": "Taux directeur: choc de taux et cout du credit"},
    {"variable": "CPI", "fred_series": "CPIAUCSL", "frequency": "M", "role": "Source CPI_change", "business_use": "Inflation annuelle"},
    {"variable": "GDPC1", "fred_series": "GDPC1", "frequency": "Q", "role": "Source GDPC1_growth", "business_use": "Cycle economique reel"},
    {"variable": "GDPC1_growth", "fred_series": "GDPC1", "frequency": "Q->M", "role": "Predictor PD/stress", "business_use": "Contraction PIB: hausse attendue du risque"},
    {"variable": "HY_SPREAD", "fred_series": "BAMLH0A0HYM2", "frequency": "D->M", "role": "Predictor PD/LGD", "business_use": "Tension marche credit high-yield"},
    {"variable": "DRCCLACBS", "fred_series": "DRCCLACBS", "frequency": "Q->M", "role": "Calibration target", "business_use": "Taux officiel de delinquence bancaire"},
]


# ---------------------------------------------------------------------------
# 1. Chargement du portefeuille de prêts
# ---------------------------------------------------------------------------
def load_loan_data(path: str | Path | None = None, chunksize: int = 200_000) -> pd.DataFrame:
    """
    Charge loan.csv en chunks pour gérer 1.2 Go sans saturer la RAM.
    Sélectionne uniquement les colonnes utiles dès la lecture.
    """
    path = path or DATA_DIR / "loan.csv"
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {path}")

    # Lire seulement les colonnes existantes (certaines peuvent manquer selon la version)
    header = pd.read_csv(path, nrows=0)
    cols = [c for c in LOAN_COLS if c in header.columns]

    chunks = []
    for chunk in pd.read_csv(
        path,
        usecols=cols,
        chunksize=chunksize,
        low_memory=False,
        on_bad_lines="skip",
    ):
        chunks.append(chunk)

    df = pd.concat(chunks, ignore_index=True)
    print(f"[load_loan_data] {len(df):,} lignes × {df.shape[1]} colonnes chargées")
    return df


# ---------------------------------------------------------------------------
# 2. Chargement des variables macro
# ---------------------------------------------------------------------------
def load_macro_data() -> pd.DataFrame:
    """
    Charge et fusionne toutes les séries macro en un DataFrame mensuel unifié.
    Retourne un DataFrame indexé par date (fréquence mensuelle 'MS').
    """
    def _read(fname, value_col, freq="M"):
        fpath = MACRO_DIR / fname
        if not fpath.exists():
            print(f"  [WARN] {fname} introuvable, ignoré")
            return None
        df = pd.read_csv(fpath, parse_dates=[0], index_col=0)
        df.index = pd.DatetimeIndex(df.index)
        df.columns = [value_col]
        df = df[~df.index.duplicated()]
        if freq == "Q":
            df = df.resample("MS").interpolate("linear")
        elif freq == "D":
            df = df.resample("MS").mean()
        else:
            df = df.resample("MS").last()
        return df

    frames = [
        _read("UNRATE.csv",       "UNRATE",    "M"),
        _read("FEDFUNDS.csv",     "FEDFUNDS",  "M"),
        _read("CPIAUCSL.csv",     "CPI",       "M"),
        _read("GDPC1.csv",        "GDPC1",     "Q"),
        _read("GDP.csv",          "GDP",       "Q"),
        _read("DRCCLACBS.csv",    "DRCCLACBS", "Q"),
        _read("BAMLH0A0HYM2.csv", "HY_SPREAD", "D"),
    ]

    macro = pd.concat([f for f in frames if f is not None], axis=1)
    macro = macro.sort_index()

    # Croissance annuelle du PIB reel. Apres resampling mensuel, 12 periodes
    # correspondent a un vrai YoY; pct_change(4) etait un decalage de 4 mois.
    macro["GDPC1_growth"] = macro["GDPC1"].pct_change(12) * 100

    # Variation annuelle CPI
    macro["CPI_change"] = macro["CPI"].pct_change(12) * 100

    macro = macro.interpolate("linear").ffill().bfill()
    print(f"[load_macro_data] {len(macro)} points mensuels, colonnes : {list(macro.columns)}")
    return macro


# ---------------------------------------------------------------------------
# 3. Nettoyage et feature engineering
# ---------------------------------------------------------------------------
def _parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    for col in ["issue_d", "earliest_cr_line", "last_pymnt_d"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format="%b-%Y", errors="coerce")
    return df


def _parse_rates(df: pd.DataFrame) -> pd.DataFrame:
    if "int_rate" in df.columns and df["int_rate"].dtype == object:
        df["int_rate"] = df["int_rate"].str.replace("%", "", regex=False).astype(float)
    if "revol_util" in df.columns and df["revol_util"].dtype == object:
        df["revol_util"] = df["revol_util"].str.replace("%", "", regex=False).astype(float)
    return df


def _encode_categories(df: pd.DataFrame) -> pd.DataFrame:
    df["grade_num"] = df["grade"].map(GRADE_MAP)

    # Sub-grade ordinal (A1=1 … G5=35)
    subgrade_map = {
        f"{g}{n}": i * 5 + n
        for i, g in enumerate("ABCDEFG")
        for n in range(1, 6)
    }
    if "sub_grade" in df.columns:
        df["subgrade_num"] = df["sub_grade"].map(subgrade_map)

    df["emp_length_num"] = df["emp_length"].map(EMP_MAP)
    if "verification_status" in df.columns:
        df["verif_status_num"] = df["verification_status"].map(VERIF_MAP).fillna(0).astype(int)
    else:
        df["verif_status_num"] = pd.Series(0, index=df.index)

    # Terme → entier (months)
    if "term" in df.columns:
        df["term_months"] = df["term"].str.extract(r"(\d+)").astype(float)

    # Home ownership — one-hot (RENT, OWN vs MORTGAGE baseline)
    if "home_ownership" in df.columns:
        ho = pd.get_dummies(df["home_ownership"], prefix="ho", drop_first=False)
        for c in ["ho_RENT", "ho_OWN", "ho_MORTGAGE"]:
            if c not in ho.columns:
                ho[c] = 0
        df["ho_RENT"] = ho["ho_RENT"].astype(int)
        df["ho_OWN"] = ho["ho_OWN"].astype(int)

    return df


def _feature_engineering(df: pd.DataFrame) -> pd.DataFrame:
    # Ancienneté crédit en mois
    if "earliest_cr_line" in df.columns and "issue_d" in df.columns:
        df["credit_age_months"] = (
            (df["issue_d"] - df["earliest_cr_line"]).dt.days / 30
        ).clip(lower=0).fillna(0).astype(int)

    # Log revenu annuel
    df["log_annual_inc"] = np.log1p(df["annual_inc"].clip(lower=0))

    if "issue_d" in df.columns:
        df["vintage_year"] = df["issue_d"].dt.year
        df["vintage_quarter"] = df["issue_d"].dt.to_period("Q").astype(str)

    if "issue_d" in df.columns and "last_pymnt_d" in df.columns:
        last_obs = df["last_pymnt_d"].fillna(df["last_pymnt_d"].max())
        df["observation_months"] = (
            (last_obs - df["issue_d"]).dt.days / 30.4375
        ).clip(lower=0)
        df["mature_12m_flag"] = (df["observation_months"] >= 12).astype(int)
        df["mature_24m_flag"] = (df["observation_months"] >= 24).astype(int)

    return df


def _handle_outliers(df: pd.DataFrame) -> pd.DataFrame:
    # annual_inc : cap 99e percentile
    p99 = df["annual_inc"].quantile(0.99)
    df["annual_inc"] = df["annual_inc"].clip(upper=p99)

    # revol_util : cap à 100%
    if "revol_util" in df.columns:
        df["revol_util"] = df["revol_util"].clip(0, 100)

    # dti : cap 99e percentile
    if "dti" in df.columns:
        p99_dti = df["dti"].quantile(0.99)
        df["dti"] = df["dti"].clip(upper=p99_dti)

    return df


def _impute_missing(df: pd.DataFrame) -> pd.DataFrame:
    # Par médiane par grade
    for col in ["dti", "revol_util", "revol_bal"]:
        if col in df.columns:
            df[col] = df.groupby("grade_num")[col].transform(
                lambda x: x.fillna(x.median())
            )
            df[col] = df[col].fillna(df[col].median())

    # Valeur 0 pour absence de délinquance
    for col in ["delinq_2yrs", "pub_rec", "acc_now_delinq", "chargeoff_within_12_mths"]:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    # Médiane globale
    for col in ["open_acc", "total_acc", "emp_length_num", "credit_age_months", "subgrade_num"]:
        if col in df.columns:
            df[col] = df[col].fillna(df[col].median())

    df["term_months"] = df["term_months"].fillna(36)

    return df


# ---------------------------------------------------------------------------
# 4. Variables cibles : default_flag, stage, LGD, EAD
# ---------------------------------------------------------------------------
def _add_targets(df: pd.DataFrame) -> pd.DataFrame:
    # Flag de défaut
    df["default_flag"] = df["loan_status"].isin(DEFAULT_STATUS).astype(int)

    # Staging IFRS 9
    df["stage"] = df["loan_status"].map(STAGE_MAP).fillna(1).astype(int)

    if "mature_12m_flag" in df.columns:
        df["default_12m_observed"] = np.where(
            df["mature_12m_flag"].eq(1), df["default_flag"], np.nan
        )
    if "mature_24m_flag" in df.columns:
        df["default_24m_observed"] = np.where(
            df["mature_24m_flag"].eq(1), df["default_flag"], np.nan
        )

    return df


def _compute_lgd_ead(df: pd.DataFrame, ead_method: str = "initial") -> pd.DataFrame:
    # EAD = capital restant dû
    if ead_method not in {"initial", "snapshot"}:
        raise ValueError("ead_method doit etre 'initial' ou 'snapshot'")

    if ead_method == "snapshot" and "out_prncp" in df.columns:
        df["EAD"] = df["out_prncp"].fillna(df["funded_amnt"]).fillna(df["loan_amnt"])
    else:
        df["EAD"] = df["funded_amnt"].fillna(df["loan_amnt"])

    # LGD empirique sur prêts défaillants
    mask = df["default_flag"] == 1
    rec = (df.loc[mask, "total_rec_prncp"].fillna(0)
           + df.loc[mask, "recoveries"].fillna(0))
    base = df.loc[mask, "funded_amnt"].replace(0, np.nan)
    df.loc[mask, "recovery_rate"] = (rec / base).clip(0, 1)
    df.loc[mask, "LGD"] = 1 - df.loc[mask, "recovery_rate"]

    # LGD proxy par grade pour les non-défaillants
    lgd_by_grade = df.loc[mask].groupby("grade_num")["LGD"].mean()
    df.loc[~mask, "LGD"] = df.loc[~mask, "grade_num"].map(lgd_by_grade)

    # Valeur de repli si grade inconnu
    df["LGD"] = df["LGD"].fillna(df["LGD"].median()).clip(0, 1)

    return df


# ---------------------------------------------------------------------------
# 5. Fusion macro
# ---------------------------------------------------------------------------
def _merge_macro(df: pd.DataFrame, macro: pd.DataFrame) -> pd.DataFrame:
    df["year_month"] = df["issue_d"].dt.to_period("M")
    macro_m = macro.copy()
    macro_m.index = macro_m.index.to_period("M")
    macro_m.index.name = "year_month"
    macro_reset = macro_m.reset_index()

    df = df.merge(macro_reset, on="year_month", how="left")
    return df


def validate_raw_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Controle les colonnes minimales avant preprocessing."""
    rows = []
    for col, expected_type in EXPECTED_SCHEMA.items():
        exists = col in df.columns
        missing_rate = float(df[col].isna().mean()) if exists else np.nan
        dtype = str(df[col].dtype) if exists else ""
        rows.append({
            "column": col,
            "expected_type": expected_type,
            "exists": exists,
            "dtype": dtype,
            "missing_rate": round(missing_rate, 4) if exists else np.nan,
            "status": "OK" if exists else "MISSING",
        })
    return pd.DataFrame(rows)


def build_eda_quality_tables(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """
    Tables EDA/preprocessing a presenter: censure, missing values,
    outliers et risque par vintage.
    """
    tables: dict[str, pd.DataFrame] = {}

    tables["feature_missing_report"] = (
        df.isna().mean().sort_values(ascending=False).rename("missing_rate")
        .reset_index().rename(columns={"index": "column"})
    )

    numeric_cols = [
        c for c in ["loan_amnt", "funded_amnt", "annual_inc", "dti", "revol_util",
                    "int_rate", "EAD", "LGD", "observation_months"]
        if c in df.columns
    ]
    if numeric_cols:
        tables["outlier_summary"] = df[numeric_cols].describe(
            percentiles=[0.01, 0.05, 0.5, 0.95, 0.99]
        ).T.reset_index().rename(columns={"index": "column"})

    if {"vintage_year", "default_flag"}.issubset(df.columns):
        tables["vintage_default_profile"] = df.groupby("vintage_year").agg(
            loans=("default_flag", "count"),
            default_rate=("default_flag", "mean"),
            mature_12m_rate=("mature_12m_flag", "mean") if "mature_12m_flag" in df.columns else ("default_flag", "mean"),
            obs_months_median=("observation_months", "median") if "observation_months" in df.columns else ("default_flag", "mean"),
        ).reset_index()

    miss_cols = [c for c in ["dti", "revol_util", "annual_inc"] if c in df.columns]
    if "vintage_year" in df.columns and miss_cols:
        tables["missing_by_year"] = (
            df.groupby("vintage_year")[miss_cols]
            .apply(lambda x: x.isna().mean())
            .reset_index()
        )

    return tables


def save_preprocessing_reports(
    df: pd.DataFrame,
    raw_schema: pd.DataFrame,
    reports_dir: Path = PREPROCESSING_REPORTS_DIR,
) -> dict[str, Path]:
    """Sauvegarde les controles EDA/preprocessing en CSV."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    paths = {"schema_quality_report": reports_dir / "schema_quality_report.csv"}
    raw_schema.to_csv(paths["schema_quality_report"], index=False)

    paths["fred_variable_dictionary"] = reports_dir / "fred_variable_dictionary.csv"
    pd.DataFrame(FRED_VARIABLE_DICTIONARY).to_csv(
        paths["fred_variable_dictionary"], index=False
    )

    for name, table in build_eda_quality_tables(df).items():
        path = reports_dir / f"{name}.csv"
        table.to_csv(path, index=False)
        paths[name] = path

    audit = pd.DataFrame([{
        "n_rows": len(df),
        "n_columns": df.shape[1],
        "default_rate": df["default_flag"].mean() if "default_flag" in df.columns else np.nan,
        "stage_3_rate": (df["stage"] == 3).mean() if "stage" in df.columns else np.nan,
        "ead_total": df["EAD"].sum() if "EAD" in df.columns else np.nan,
        "lgd_median": df["LGD"].median() if "LGD" in df.columns else np.nan,
        "mature_12m_rate": df["mature_12m_flag"].mean() if "mature_12m_flag" in df.columns else np.nan,
    }])
    paths["preprocessing_audit"] = reports_dir / "preprocessing_audit.csv"
    audit.to_csv(paths["preprocessing_audit"], index=False)
    return paths


def save_clean_data_quality_reports(
    df: pd.DataFrame,
    reports_dir: Path = PREPROCESSING_REPORTS_DIR,
) -> dict[str, Path]:
    """
    Sauvegarde les controles EDA/preprocessing a partir d'un dataset deja nettoye.

    Cette fonction sert aux scripts de maintenance lorsque le parquet nettoye existe
    deja et qu'on ne veut pas recharger loan.csv.
    """
    schema = pd.DataFrame({
        "column": df.columns,
        "present": True,
        "expected_type": "cleaned_output",
        "observed_dtype": [str(dtype) for dtype in df.dtypes],
        "missing_pct": df.isna().mean().round(4).values,
        "status": "INFO",
    })
    return save_preprocessing_reports(df, schema, reports_dir=reports_dir)


# ---------------------------------------------------------------------------
# 6. Pipeline complet
# ---------------------------------------------------------------------------
def build_clean_dataset(
    loan_path: str | Path | None = None,
    save_parquet: bool = True,
    save_reports: bool = True,
    ead_method: str = "initial",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Pipeline complet : charge, nettoie, encode, calcule LGD/EAD/stage, fusionne macro.

    Returns
    -------
    df : DataFrame propre (portefeuille + macro)
    macro : DataFrame variables macro brutes (mensuelles)
    """
    print("=== Chargement des données ===")
    df = load_loan_data(loan_path)
    raw_schema = validate_raw_schema(df)
    macro = load_macro_data()

    print("\n=== Parsing dates et taux ===")
    df = _parse_dates(df)
    df = _parse_rates(df)

    print("=== Filtrage : supprimer les lignes sans issue_d ===")
    df = df.dropna(subset=["issue_d"])

    print("=== Encodage catégories ===")
    df = _encode_categories(df)

    print("=== Feature engineering ===")
    df = _feature_engineering(df)

    print("=== Gestion des outliers ===")
    df = _handle_outliers(df)

    print("=== Imputation des valeurs manquantes ===")
    df = _impute_missing(df)

    print("=== Variables cibles (default_flag, stage) ===")
    df = _add_targets(df)

    print("=== Calcul LGD et EAD empiriques ===")
    df = _compute_lgd_ead(df, ead_method=ead_method)

    print("=== Fusion variables macro ===")
    df = _merge_macro(df, macro)

    if save_reports:
        report_paths = save_preprocessing_reports(df, raw_schema)
        print(f"=== Rapports EDA/preprocessing : {len(report_paths)} fichiers CSV ===")

    print(f"\n=== Dataset final : {len(df):,} lignes × {df.shape[1]} colonnes ===")
    print(f"   Taux de défaut global : {df['default_flag'].mean():.2%}")
    print(f"   Distribution stages   : {df['stage'].value_counts().to_dict()}")
    print(f"   LGD médiane           : {df['LGD'].median():.2%}")
    print(f"   EAD total (M$)        : {df['EAD'].sum() / 1e6:,.1f}")

    if save_parquet:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTPUT_DIR / "loan_clean.parquet"
        # Ne sauvegarder que les colonnes utiles pour éviter ArrowMemoryError
        # lors du rechargement (évite de stocker les 50+ colonnes brutes)
        save_cols = [
            # Identifiants / métadonnées
            "loan_amnt", "grade", "issue_d", "term_months",
            "vintage_year", "vintage_quarter", "observation_months",
            "mature_12m_flag", "mature_24m_flag",
            # Features PD (20 variables)
            "grade_num", "subgrade_num", "dti", "revol_util", "int_rate",
            "delinq_2yrs", "log_annual_inc", "credit_age_months", "pub_rec",
            "open_acc", "emp_length_num", "verif_status_num",
            "ho_RENT", "ho_OWN",
            # Variables macro
            "UNRATE", "GDPC1_growth", "FEDFUNDS", "HY_SPREAD", "CPI_change", "DRCCLACBS",
            # Variables cibles IFRS 9
            "default_flag", "default_12m_observed", "default_24m_observed",
            "stage", "LGD", "EAD",
        ]
        cols_to_save = [c for c in save_cols if c in df.columns]
        df[cols_to_save].to_parquet(out, index=False, compression="snappy")
        print(f"\n[Sauvegarde] {out} ({len(cols_to_save)} colonnes)")

    return df, macro


# ---------------------------------------------------------------------------
# 7. Utilitaires
# ---------------------------------------------------------------------------
def get_pd_features(df: pd.DataFrame) -> list[str]:
    """Retourne la liste des features pour le modèle PD (sans data leakage)."""
    candidates = [
        "grade_num", "subgrade_num", "dti", "revol_util", "int_rate",
        "delinq_2yrs", "log_annual_inc", "credit_age_months", "pub_rec",
        "open_acc", "term_months", "emp_length_num", "verif_status_num",
        "ho_RENT", "ho_OWN",
        "UNRATE", "GDPC1_growth", "FEDFUNDS", "HY_SPREAD", "CPI_change",
    ]
    return [c for c in candidates if c in df.columns]


def get_origination_pd_features(df: pd.DataFrame) -> list[str]:
    """
    Features disponibles a l'octroi ou au mois d'emission. Exclut les variables
    post-origination pour reduire le leakage dans les modeles PD.
    """
    return [c for c in get_pd_features(df) if c not in POST_ORIGINATION_COLS]


def get_temporal_split(df: pd.DataFrame, train_end: str = "2014-12-31",
                       val_end: str = "2016-12-31"):
    """Split temporel sans data leakage."""
    train = df[df["issue_d"] <= train_end].copy()
    val   = df[(df["issue_d"] > train_end) & (df["issue_d"] <= val_end)].copy()
    test  = df[df["issue_d"] > val_end].copy()
    print(f"Split — Train: {len(train):,} | Val: {len(val):,} | Test: {len(test):,}")
    return train, val, test


def compute_psi(expected: np.ndarray, actual: np.ndarray, n_bins: int = 10) -> float:
    """
    Population Stability Index (PSI).
    PSI < 0.10 : stable | 0.10-0.25 : léger changement | > 0.25 : instable
    """
    breakpoints = np.percentile(expected, np.linspace(0, 100, n_bins + 1))
    breakpoints = np.unique(breakpoints)

    def _pct(arr):
        counts, _ = np.histogram(arr, bins=breakpoints)
        pct = counts / len(arr)
        return np.where(pct == 0, 1e-6, pct)

    e_pct = _pct(expected)
    a_pct = _pct(actual)
    return float(np.sum((a_pct - e_pct) * np.log(a_pct / e_pct)))


if __name__ == "__main__":
    df, macro = build_clean_dataset()
