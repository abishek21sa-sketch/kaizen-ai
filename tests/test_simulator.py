from kaizen_factory.models import FactoryConfig
from kaizen_factory.simulator import simulate_factory


def test_deterministic_observable_records_for_fixed_seed_and_scenario():
    cfg = FactoryConfig(seed=123, units=700)
    a = simulate_factory(cfg, "fixture_wear_temp")
    b = simulate_factory(cfg, "fixture_wear_temp")
    assert a.records == b.records
    assert a.run_id != b.run_id


def test_pre_incident_records_are_identical_across_fault_scenarios():
    cfg = FactoryConfig(seed=77, units=800, activation_fraction=0.4)
    a = simulate_factory(cfg, "fixture_wear_temp")
    b = simulate_factory(cfg, "tool_calibration_drift")
    assert a.records[: a.activation_unit] == b.records[: b.activation_unit]


def test_causal_firewall_keeps_latent_values_out_of_observable_records():
    r = simulate_factory(FactoryConfig(seed=8, units=500), "gage_measurement_drift")
    keys = set(r.records[0])
    forbidden = {
        "torque_actual_nm",
        "alignment_actual_mm",
        "adhesive_strength_actual_mpa",
        "true_defect",
        "latent_fault_strength",
        "measurement_bias_nm",
        "microstop_s",
        "changeover_extra_s",
    }
    assert not (keys & forbidden)
    assert r.ground_truth["causal_firewall"]["observable_records_contain_latent_values"] is False


def test_fixture_wear_fault_degrades_observed_quality():
    r = simulate_factory(FactoryConfig(seed=42, units=1200), "fixture_wear_temp")
    pre = r.public_summary["pre_incident"]["observed_defect_rate"]
    post = r.public_summary["post_incident"]["observed_defect_rate"]
    assert post > pre + 0.05


def test_supplier_shift_degrades_observed_quality():
    r = simulate_factory(FactoryConfig(seed=42, units=1200), "supplier_resin_shift")
    assert r.public_summary["post_incident"]["observed_defect_rate"] > 0.08


def test_gage_drift_creates_false_reject_gap_without_physical_shift():
    r = simulate_factory(FactoryConfig(seed=42, units=1200), "gage_measurement_drift")
    observed = r.public_summary["post_incident"]["observed_defect_rate"]
    true_rate = r.ground_truth["latent_summary"]["post_incident"]["true_defect_rate"]
    assert observed - true_rate > 0.05


def test_microstops_create_queue_growth_with_stable_quality():
    r = simulate_factory(FactoryConfig(seed=42, units=1200), "calibration_microstops")
    pre = r.public_summary["pre_incident"]
    post = r.public_summary["post_incident"]
    assert post["avg_queue_wait_s"] > pre["avg_queue_wait_s"] + 50
    assert abs(post["observed_defect_rate"] - pre["observed_defect_rate"]) < 0.03


def test_changeover_deterioration_is_sequence_dependent_in_latent_store():
    r = simulate_factory(FactoryConfig(seed=42, units=1000), "changeover_deterioration")
    pre = r.latent_records[: r.activation_unit]
    post = r.latent_records[r.activation_unit :]
    assert all(x["changeover_extra_s"] == 0 for x in pre)
    assert any(x["changeover_extra_s"] > 0 for x in post)


def test_configuration_validation():
    bad = FactoryConfig(units=50)
    try:
        simulate_factory(bad, "fixture_wear_temp")
    except ValueError as e:
        assert "at least 100" in str(e)
    else:
        raise AssertionError("Expected ValueError")
