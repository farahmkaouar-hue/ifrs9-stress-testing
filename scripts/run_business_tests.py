import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.test_stress_engine import (  # noqa: E402
    test_banking_core_adds_segments_rwa_and_basel_metrics,
    test_dynamic_projection_returns_yearly_ecl_cet1_and_stage_mix,
    test_forward_looking_summary_weighted_total,
    test_historical_scenarios_are_active_without_duplicate_macro_alias,
    test_cet1_impact_includes_shortfall_and_management_action,
    test_lgd_and_ead_do_not_decrease_under_adverse_stress,
    test_markov_rows_sum_to_one,
    test_pd_stress_fallback_uses_existing_pd_pred_without_models,
    test_scenario_path_has_requested_horizon_and_macro_columns,
    test_scenario_design_marks_adverse_as_coherent,
    test_stress_model_comparison_selects_a_champion,
    test_stress_output_validation_flags_bad_outputs,
)
from tests.test_preprocessing_quality import (  # noqa: E402
    test_clean_data_quality_reports_write_expected_files,
    test_eda_quality_tables_cover_missing_outliers_and_vintage,
    test_lgd_ead_snapshot_uses_remaining_principal_when_available,
    test_origination_features_exclude_post_origination_leakage,
    test_raw_schema_detects_missing_required_columns,
)


TESTS = [
    test_scenario_design_marks_adverse_as_coherent,
    test_lgd_and_ead_do_not_decrease_under_adverse_stress,
    test_markov_rows_sum_to_one,
    test_stress_output_validation_flags_bad_outputs,
    test_forward_looking_summary_weighted_total,
    test_historical_scenarios_are_active_without_duplicate_macro_alias,
    test_cet1_impact_includes_shortfall_and_management_action,
    test_stress_model_comparison_selects_a_champion,
    test_pd_stress_fallback_uses_existing_pd_pred_without_models,
    test_scenario_path_has_requested_horizon_and_macro_columns,
    test_dynamic_projection_returns_yearly_ecl_cet1_and_stage_mix,
    test_banking_core_adds_segments_rwa_and_basel_metrics,
    test_raw_schema_detects_missing_required_columns,
    test_eda_quality_tables_cover_missing_outliers_and_vintage,
    test_lgd_ead_snapshot_uses_remaining_principal_when_available,
    test_origination_features_exclude_post_origination_leakage,
    test_clean_data_quality_reports_write_expected_files,
]


if __name__ == "__main__":
    for test in TESTS:
        test()
        print(f"OK - {test.__name__}")
    print(f"{len(TESTS)} business tests passed.")
