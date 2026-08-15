import math

from kaizen_factory.models import FactoryConfig
from kaizen_factory.simulator import simulate_factory
from kaizen_quality.capability import capability_analysis
from kaizen_quality.data_quality import data_quality_report
from kaizen_quality.msa import crossed_gage_rr, generate_baseline_msa_study
from kaizen_quality.pareto import pareto_and_copq
from kaizen_quality.spc import individuals_mr_chart, p_chart


def test_capability_reference_case_matches_hand_calculation():
    values = [9.8, 10.1, 10.0, 10.2, 9.9]
    r = capability_analysis(values, lsl=9.0, usl=11.0)
    mrbar = (0.3 + 0.1 + 0.2 + 0.3) / 4
    sigma_within = mrbar / 1.128
    expected_cp = 2.0 / (6 * sigma_within)
    expected_cpk = min((11 - 10.0) / (3 * sigma_within), (10.0 - 9) / (3 * sigma_within))
    assert math.isclose(r["cp"], expected_cp, rel_tol=1e-12)
    assert math.isclose(r["cpk"], expected_cpk, rel_tol=1e-12)


def test_one_sided_capability_has_no_cp_but_has_cpk():
    r = capability_analysis([5.8, 5.9, 6.0, 6.1, 5.95], lsl=5.4)
    assert r["cp"] is None
    assert r["cpk"] is not None
    assert r["cpl"] == r["cpk"]


def test_imr_reference_limits():
    values = [1.0, 1.2, 0.9, 1.1]
    r = individuals_mr_chart(values, baseline_n=4)
    mrbar = (0.2 + 0.3 + 0.2) / 3
    sigma = mrbar / 1.128
    assert math.isclose(r["center"], 1.05, rel_tol=1e-12)
    assert math.isclose(r["ucl"], 1.05 + 3 * sigma, rel_tol=1e-12)
    assert math.isclose(r["mr_ucl"], 3.267 * mrbar, rel_tol=1e-12)


def test_p_chart_flags_extreme_post_subgroup():
    flags = [False] * 90 + [True] * 10 + [True] * 40 + [False] * 10
    r = p_chart(flags, subgroup_size=50, baseline_n=100)
    assert r["center"] == 0.10
    assert r["groups"][2]["signal"] is True


def test_pareto_splits_multidefect_and_preserves_quality_cost():
    records = [
        {"observed_defect": True, "defect_type": "TORQUE+ALIGNMENT", "rework": True, "scrap": False, "copq_usd": 46.0},
        {"observed_defect": True, "defect_type": "TORQUE", "rework": False, "scrap": True, "copq_usd": 215.0},
        {"observed_defect": False, "defect_type": "NONE", "rework": False, "scrap": False, "copq_usd": 5.0},
    ]
    r = pareto_and_copq(records)
    counts = {x["defect_family"]: x["occurrences"] for x in r["pareto"]}
    assert counts == {"TORQUE": 2, "ALIGNMENT": 1}
    assert r["copq"]["quality_usd"] == 261.0
    assert r["copq"]["flow_delay_usd"] == 5.0


def test_data_quality_passes_factory_observable_records():
    run = simulate_factory(FactoryConfig(seed=42, units=400), "fixture_wear_temp")
    r = data_quality_report(run.records)
    assert r["status"] == "PASS"
    assert r["score"] == 100.0


def test_crossed_gage_rr_balanced_reference_study():
    readings = []
    part_values = {"P1": 9.0, "P2": 10.0, "P3": 11.0}
    app_bias = {"A": 0.0, "B": 0.05}
    noise = [-0.02, 0.02]
    for p, base in part_values.items():
        for a, bias in app_bias.items():
            for rep, eps in enumerate(noise, 1):
                readings.append({"part": p, "appraiser": a, "repeat": rep, "value": base + bias + eps})
    r = crossed_gage_rr(readings)
    assert r["design"] == {"parts": 3, "appraisers": 2, "repeats": 2, "readings": 12}
    assert r["pct_study_variation_grr"] < 10
    assert r["ndc"] >= 5


def test_generated_msa_study_is_deterministic_and_uses_no_latent_input():
    run = simulate_factory(FactoryConfig(seed=99, units=500), "gage_measurement_drift")
    a = generate_baseline_msa_study(run.records, run.activation_unit, run.config.seed)
    b = generate_baseline_msa_study(run.records, run.activation_unit, run.config.seed)
    assert a == b
    assert "measurement_bias_nm" not in str(a)
    assert "torque_actual_nm" not in str(a)
