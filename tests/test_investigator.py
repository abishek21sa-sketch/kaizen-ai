from kaizen_factory.models import FactoryConfig
from kaizen_factory.simulator import simulate_factory
from kaizen_investigator import build_investigation_overview

EXPECTED_TOP = {
    "tool_calibration_drift": "MACHINE_TORQUE_BIAS",
    "fixture_wear_temp": "FIXTURE_ENVIRONMENT_INTERACTION",
    "supplier_resin_shift": "SUPPLIER_HUMIDITY_INTERACTION",
    "gage_measurement_drift": "GAGE_MEASUREMENT_DRIFT",
    "calibration_microstops": "CALIBRATION_INTERMITTENT_LOSS",
    "changeover_deterioration": "SEQUENCE_CHANGEOVER_LOSS",
}


def test_investigator_identifies_each_known_benchmark_family_without_truth_input():
    for scenario, expected in EXPECTED_TOP.items():
        result = simulate_factory(FactoryConfig(seed=42, units=700), scenario)
        inv = build_investigation_overview(result.records, result.activation_unit)
        assert inv["top_suspect"]["code"] == expected, (scenario, inv["top_suspect"])
        assert inv["top_suspect"]["causal_status"] == "NOT_CONFIRMED"
        assert inv["causality_gate"]["causal_verdict"] == "OBSERVATIONAL_SUSPECT_ONLY"
        assert inv["causality_gate"]["levels"][-1]["passed"] is False


def test_investigator_output_contains_no_latent_or_ground_truth_fields():
    result = simulate_factory(FactoryConfig(seed=9, units=700), "fixture_wear_temp")
    inv = build_investigation_overview(result.records, result.activation_unit)
    serialized = str(inv).lower()
    forbidden = [
        "latent_fault_strength",
        "torque_actual_nm",
        "true_defect",
        "measurement_bias_nm",
        "fixture_wear_temp",
        "root_cause",
        "causal_graph",
    ]
    for token in forbidden:
        assert token not in serialized
    assert inv["methodology"]["scenario_code_available"] is False
    assert inv["methodology"]["latent_ground_truth_available"] is False


def test_evidence_ledger_is_structured_and_p_values_are_valid():
    result = simulate_factory(FactoryConfig(seed=42, units=700), "tool_calibration_drift")
    inv = build_investigation_overview(result.records, result.activation_unit)
    assert len(inv["ranked_hypotheses"]) == 6
    assert len(inv["evidence_ledger"]) >= 18
    assert len({x["evidence_id"] for x in inv["evidence_ledger"]}) == len(inv["evidence_ledger"])
    for ev in inv["evidence_ledger"]:
        p = ev["p_value"]
        if p is not None:
            assert 0 <= p <= 1
        assert ev["role"] in {"PRIMARY", "CORROBORATING"}


def test_changeover_and_microstop_are_statistically_distinguished():
    c = simulate_factory(FactoryConfig(seed=17, units=900), "changeover_deterioration")
    ci = build_investigation_overview(c.records, c.activation_unit)
    assert ci["top_suspect"]["code"] == "SEQUENCE_CHANGEOVER_LOSS"

    m = simulate_factory(FactoryConfig(seed=17, units=900), "calibration_microstops")
    mi = build_investigation_overview(m.records, m.activation_unit)
    assert mi["top_suspect"]["code"] == "CALIBRATION_INTERMITTENT_LOSS"


def test_evidence_score_is_declared_non_probabilistic():
    result = simulate_factory(FactoryConfig(seed=5, units=700), "gage_measurement_drift")
    inv = build_investigation_overview(result.records, result.activation_unit)
    note = inv["methodology"]["evidence_score_note"].lower()
    assert "not a probability" in note
    assert 0 <= inv["top_suspect"]["evidence_score"] <= 100


def test_adjusted_models_anova_regression_and_confidence_intervals_are_present():
    result = simulate_factory(FactoryConfig(seed=42, units=700), "tool_calibration_drift")
    inv = build_investigation_overview(result.records, result.activation_unit)
    models = inv["adjusted_models"]
    assert models["models_fit"] >= 4
    assert models["anova"]["status"] == "FIT"
    assert len(models["anova"]["terms"]) >= 4
    assert any(m["status"] == "FIT" and m["coefficients"] for m in models["ols"])
    assert models["logistic"]["status"] == "FIT"
    assert any(ev["confidence_interval_95"] is not None for ev in inv["evidence_ledger"])
    assert len(inv["test_router"]) == 6


def test_asset_attribution_does_not_choose_equal_and_opposite_complement():
    # Regression for V0.4.1: a two-level DID is antisymmetric. The unaffected
    # complement must not be named merely because its absolute contrast ties.
    for seed in [3, 7, 17, 42, 113, 2718]:
        tool = simulate_factory(FactoryConfig(seed=seed, units=900), "tool_calibration_drift")
        tool_inv = build_investigation_overview(tool.records, tool.activation_unit)
        assert tool_inv["top_suspect"]["code"] == "MACHINE_TORQUE_BIAS"
        assert tool_inv["top_suspect"]["target"] == "M2"
        assert tool_inv["top_suspect"]["attribution"]["direction"] == "INCREASE"

        gage = simulate_factory(FactoryConfig(seed=seed, units=900), "gage_measurement_drift")
        gage_inv = build_investigation_overview(gage.records, gage.activation_unit)
        assert gage_inv["top_suspect"]["code"] == "GAGE_MEASUREMENT_DRIFT"
        assert gage_inv["top_suspect"]["target"] == "G2"
        assert gage_inv["top_suspect"]["attribution"]["direction"] == "INCREASE"


def test_seed42_tool_drift_asset_matches_observable_direction_without_truth_input():
    result = simulate_factory(FactoryConfig(seed=42, units=2500), "tool_calibration_drift")
    inv = build_investigation_overview(result.records, result.activation_unit)
    top = inv["top_suspect"]
    assert top["code"] == "MACHINE_TORQUE_BIAS"
    assert top["target"] == "M2"
    assert top["attribution"]["observed_change"] > 0
    assert top["attribution"]["selection_basis"].startswith("DID magnitude")
