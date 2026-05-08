import numpy as np
import pandas as pd

from src.stress_scenarios import (
    ACTIVE_STRESS_SCENARIOS,
    BASELINE,
    SCENARIOS,
    SCENARIO_ADVERSE,
    compute_pd_stressed,
    compute_ead_stressed,
    compute_forward_looking_summary,
    compute_lgd_stressed,
    stressed_markov_matrix,
    validate_scenario_design,
    validate_stress_outputs,
)
from src.stress_model_comparison import compare_stress_testing_models
from src.resilience import compute_cet1_impact
from src.scenario_projection import build_scenario_path, compute_dynamic_projection
from src.banking_core import compute_basel_metrics, enrich_banking_view, segment_summary


def test_scenario_design_marks_adverse_as_coherent():
    report = validate_scenario_design({"adverse": SCENARIO_ADVERSE}, save=False)
    assert bool(report.loc[0, "economically_adverse"])
    assert report.loc[0, "pd_lift_floor"] >= 1.0


def test_lgd_and_ead_do_not_decrease_under_adverse_stress():
    df = pd.DataFrame({"LGD": [0.3, 0.6], "EAD": [100.0, 250.0]})
    lgd_s = compute_lgd_stressed(df, SCENARIO_ADVERSE)
    ead_s = compute_ead_stressed(df, SCENARIO_ADVERSE)
    assert np.all(lgd_s >= df["LGD"])
    assert np.all(ead_s >= df["EAD"])


def test_markov_rows_sum_to_one():
    matrix = stressed_markov_matrix(SCENARIO_ADVERSE)
    assert np.allclose(matrix.sum(axis=1).values, 1.0)
    assert (matrix.values >= 0).all()


def test_stress_output_validation_flags_bad_outputs():
    summary = pd.DataFrame([
        {
            "Scenario": "Bad",
            "ECL_lift": 0.9,
            "Delta_ECL_M$": -1.0,
            "PD_stressed_%": 4.0,
            "PD_baseline_%": 5.0,
            "PD_final_lift": 1.0,
            "PD_floor_lift": 1.1,
        }
    ])
    report = validate_stress_outputs(summary)
    assert report.loc[0, "validation_status"] == "REVIEW"


def test_forward_looking_summary_weighted_total():
    stress = pd.DataFrame([
        {"Scenario": "Adverse", "ECL_stressed_M$": 150.0},
        {"Scenario": "Severe", "ECL_stressed_M$": 250.0},
    ])
    result = compute_forward_looking_summary(100.0, stress, save=False)
    total = result[result["scenario_key"] == "forward_looking"]["ECL_M$"].iloc[0]
    assert np.isclose(total, 0.40 * 100.0 + 0.35 * 150.0 + 0.25 * 250.0)


def test_historical_scenarios_are_active_without_duplicate_macro_alias():
    assert "covid_2020" in SCENARIOS
    assert "market_2018" in SCENARIOS
    assert "ukraine_2022" in SCENARIOS
    assert "covid_2020" in ACTIVE_STRESS_SCENARIOS
    assert "market_2018" in ACTIVE_STRESS_SCENARIOS
    assert "ukraine_2022" in ACTIVE_STRESS_SCENARIOS
    assert "macro_shock" not in SCENARIOS
    assert "macro_shock" not in ACTIVE_STRESS_SCENARIOS


def test_stress_model_comparison_selects_a_champion():
    df = pd.DataFrame({
        "PD_pred": [0.02, 0.05, 0.10, 0.20],
        "LGD": [0.35, 0.40, 0.50, 0.60],
        "EAD": [1000.0, 1500.0, 2000.0, 2500.0],
        "term_months": [36, 36, 60, 60],
        "stage": [1, 1, 2, 3],
        "default_flag": [0, 0, 1, 1],
    })
    scored, champion = compare_stress_testing_models(
        df,
        scenario=SCENARIO_ADVERSE,
        scenario_name="adverse",
        observed_target_dr=0.12,
        save=False,
    )
    assert champion in set(scored["model_name"])
    assert "final_score" in scored.columns
    assert scored.iloc[0]["final_score"] >= scored.iloc[-1]["final_score"]


def test_pd_stress_fallback_uses_existing_pd_pred_without_models():
    df = pd.DataFrame({"PD_pred": [0.02, 0.05, 0.10]})

    stressed = compute_pd_stressed(
        df=df,
        scenario=SCENARIO_ADVERSE,
        champion_pd_model=None,
        features=[],
        satellite_model={},
        satellite_features=[],
    )

    assert len(stressed) == len(df)
    assert (stressed >= df["PD_pred"]).all()
    assert (stressed <= 1).all()


def test_cet1_impact_includes_shortfall_and_management_action():
    impact = compute_cet1_impact(
        ecl_baseline=100.0,
        ecl_stressed=500.0,
        ead_total=1000.0,
        cet1_initial=0.12,
        tax_rate=0.30,
    )
    assert "Shortfall_4_5_M$" in impact
    assert "Shortfall_7_0_M$" in impact
    assert "management_action" in impact
    assert impact["Shortfall_7_0_M$"] >= impact["Shortfall_4_5_M$"]


def test_scenario_path_has_requested_horizon_and_macro_columns():
    path = build_scenario_path(SCENARIO_ADVERSE, horizon_years=3, profile="front_loaded")
    assert list(path["year"]) == [1, 2, 3]
    assert {"UNRATE", "GDPC1_growth", "severity_score"}.issubset(path.columns)
    assert path.loc[0, "UNRATE"] >= path.loc[2, "UNRATE"]


def test_dynamic_projection_returns_yearly_ecl_cet1_and_stage_mix():
    df = pd.DataFrame({
        "PD_pred": [0.02, 0.05, 0.10, 0.20],
        "LGD": [0.35, 0.40, 0.50, 0.60],
        "EAD": [1000.0, 1500.0, 2000.0, 2500.0],
        "term_months": [36, 36, 60, 60],
        "stage": [1, 1, 2, 3],
        "ECL_ifrs9": [2.33, 7.50, 100.0, 300.0],
    })
    projection, stage_projection = compute_dynamic_projection(
        df,
        SCENARIO_ADVERSE,
        horizon_years=3,
        profile="linear",
        save=False,
    )
    assert len(projection) == 3
    assert len(stage_projection) == 3
    assert {"ECL_M$", "CET1_%", "PD_mean_%", "UNRATE"}.issubset(projection.columns)
    assert {"Stage 1_%", "Stage 2_%", "Stage 3_%"}.issubset(stage_projection.columns)
    assert projection["ECL_M$"].notna().all()
    assert "RWA_M$" in projection.columns


def test_banking_core_adds_segments_rwa_and_basel_metrics():
    df = pd.DataFrame({
        "issue_d": pd.to_datetime(["2020-01-01", "2020-02-01", "2020-03-01"]),
        "purpose": ["credit_card", "small_business", "home_improvement"],
        "grade": ["A", "F", "C"],
        "stage": [1, 2, 3],
        "loan_amnt": [10000.0, 20000.0, 30000.0],
        "EAD": [10000.0, 20000.0, 30000.0],
        "LGD": [0.3, 0.5, 0.6],
        "PD_pred": [0.02, 0.10, 0.40],
        "ECL_ifrs9": [60.0, 1000.0, 7200.0],
    })
    view, reporting_date = enrich_banking_view(df, "2020-12-31")
    assert reporting_date == pd.Timestamp("2020-12-31")
    assert {"regulatory_segment", "risk_weight", "RWA"}.issubset(view.columns)
    assert view["RWA"].sum() > 0

    metrics = compute_basel_metrics(view, cet1_ratio=0.12)
    assert metrics["RWA_M$"] > 0
    assert "Total_capital_ratio_%" in metrics

    summary = segment_summary(view)
    assert not summary.empty
    assert "RWA_density_%" in summary.columns
