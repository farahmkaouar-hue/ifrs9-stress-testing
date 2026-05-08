from pathlib import Path
import shutil

import numpy as np
import pandas as pd

from src.data_prep import (
    _compute_lgd_ead,
    build_eda_quality_tables,
    get_origination_pd_features,
    save_clean_data_quality_reports,
    validate_raw_schema,
)


def test_raw_schema_detects_missing_required_columns():
    df = pd.DataFrame({
        "loan_amnt": [1000.0],
        "funded_amnt": [1000.0],
        "term": ["36 months"],
        "int_rate": ["10.0%"],
        "grade": ["A"],
        "loan_status": ["Current"],
        "issue_d": ["Jan-2015"],
    })

    report = validate_raw_schema(df)
    missing = set(report.loc[report["status"] == "MISSING", "column"])

    assert {"sub_grade", "annual_inc", "dti"}.issubset(missing)


def test_eda_quality_tables_cover_missing_outliers_and_vintage():
    df = pd.DataFrame({
        "grade_num": [1, 2, 2],
        "annual_inc": [50000.0, 90000.0, np.nan],
        "dti": [10.0, 250.0, 12.0],
        "default_flag": [0, 1, 0],
        "vintage_year": [2018, 2018, 2019],
        "mature_12m_flag": [1, 1, 0],
    })

    tables = build_eda_quality_tables(df)

    assert "feature_missing_report" in tables
    assert "outlier_summary" in tables
    assert "vintage_default_profile" in tables
    assert "missing_by_year" in tables
    assert "annual_inc" in set(tables["feature_missing_report"]["column"])
    assert 2018 in set(tables["vintage_default_profile"]["vintage_year"])


def test_lgd_ead_snapshot_uses_remaining_principal_when_available():
    df = pd.DataFrame({
        "default_flag": [1, 0],
        "out_prncp": [200.0, 300.0],
        "funded_amnt": [1000.0, 1000.0],
        "loan_amnt": [1000.0, 1000.0],
        "total_rec_prncp": [400.0, 0.0],
        "recoveries": [100.0, 0.0],
        "grade_num": [1, 1],
    })

    result = _compute_lgd_ead(df.copy(), ead_method="snapshot")

    assert result["EAD"].tolist() == [200.0, 300.0]
    assert result.loc[0, "LGD"] == 0.5
    assert result["LGD"].between(0, 1).all()


def test_origination_features_exclude_post_origination_leakage():
    df = pd.DataFrame(columns=[
        "grade_num",
        "dti",
        "loan_status",
        "recoveries",
        "last_pymnt_d",
        "UNRATE",
    ])

    features = get_origination_pd_features(df)

    assert "grade_num" in features
    assert "UNRATE" in features
    assert "loan_status" not in features
    assert "recoveries" not in features


def test_clean_data_quality_reports_write_expected_files():
    df = pd.DataFrame({
        "annual_inc": [50000.0, np.nan],
        "dti": [10.0, 15.0],
        "default_flag": [0, 1],
        "stage": [1, 3],
        "EAD": [1000.0, 1500.0],
        "LGD": [0.3, 0.5],
    })

    tmp_path = Path.cwd() / "outputs" / "test_preprocessing_quality"
    if tmp_path.exists():
        shutil.rmtree(tmp_path)

    try:
        paths = save_clean_data_quality_reports(df, reports_dir=tmp_path)

        assert (tmp_path / "schema_quality_report.csv").exists()
        assert (tmp_path / "feature_missing_report.csv").exists()
        assert "preprocessing_audit" in paths
    finally:
        if tmp_path.exists():
            shutil.rmtree(tmp_path)
