import math

from kaizen_factory.models import FactoryConfig
from kaizen_factory.simulator import simulate_factory
from kaizen_ie import IEAssumptions, build_ie_overview
from kaizen_ie.capacity import line_balance, station_capacity
from kaizen_ie.flow import _time_weighted_count
from kaizen_ie.oee import calibration_oee


def _row(product="A", calibration=32.0, defect=False):
    return {
        "product_variant": product,
        "bearing_press_s": 24.0,
        "motor_assembly_s": 31.0,
        "adhesive_dispense_s": 27.0,
        "torque_fastening_s": 29.0,
        "calibration_s": calibration,
        "functional_test_s": 30.0,
        "final_inspection_s": 21.0,
        "observed_defect": defect,
    }


def test_takt_reference_case_is_45_seconds_and_80_uph():
    a = IEAssumptions(gross_shift_minutes=480, planned_break_minutes=30, customer_demand_units_per_shift=600)
    assert a.net_available_seconds_per_shift == 27000
    assert a.takt_seconds_per_unit == 45
    assert a.required_rate_units_per_hour == 80


def test_time_weighted_wip_reference_case():
    avg, max_wip, horizon = _time_weighted_count([(0, 10), (5, 15)])
    assert horizon == 15
    assert max_wip == 2
    assert math.isclose(avg, 20 / 15, rel_tol=1e-12)


def test_station_capacity_reference_case():
    rows = [_row(calibration=45.0) for _ in range(10)]
    out = station_capacity(rows, phase="pre", required_rate_uph=80, observed_release_rate_uph=90)
    cal = next(x for x in out["stations"] if x["station"] == "Calibration")
    assert cal["capacity_units_per_hour"] == 80.0
    assert cal["demand_utilization"] == 1.0
    assert cal["release_utilization"] == 1.125


def test_line_balance_reference_case():
    rows = [_row(calibration=45.0) for _ in range(5)]
    out = line_balance(rows, phase="pre", takt_s=45.0)
    assert out["intrinsic_cycle_time_s"] == 45.0
    assert out["takt_feasible_with_one_resource_each"] is True
    expected = (24 + 31 + 27 + 29 + 45 + 30 + 21) / (7 * 45)
    assert math.isclose(out["balance_efficiency_at_takt"], expected, rel_tol=1e-6)


def test_oee_diagnostic_does_not_invent_availability():
    rows = [_row(product="A", calibration=32.0, defect=False), _row(product="A", calibration=32.0, defect=True)]
    out = calibration_oee(rows, phase="pre")
    assert out["availability"] == 1.0
    assert out["availability_status"] == "ASSUMED_100_PERCENT"
    assert out["performance"] == 1.0
    assert out["quality"] == 0.5
    assert out["oee"] == 0.5


def test_factory_ie_little_law_closes_numerically():
    run = simulate_factory(FactoryConfig(seed=42, units=1200), "changeover_deterioration")
    out = build_ie_overview(run.records, run.activation_unit)
    assert out["flow"]["pre"]["little_law_error_pct"] < 1e-6
    assert out["flow"]["post"]["little_law_error_pct"] < 1e-6
    assert out["queueing"]["post"]["little_law_queue_error_pct"] < 1e-6
    assert out["queueing"]["post"]["little_law_cell_error_pct"] < 1e-6


def test_changeover_fault_creates_material_post_queue_and_calibration_bottleneck():
    run = simulate_factory(FactoryConfig(seed=42, units=2500), "changeover_deterioration")
    out = build_ie_overview(run.records, run.activation_unit)
    assert out["queueing"]["post"]["mean_wait_s"] > out["queueing"]["pre"]["mean_wait_s"] * 100
    assert out["capacity"]["post"]["bottleneck"]["station"] == "Calibration"
    assert out["capacity"]["post"]["bottleneck"]["release_utilization"] > 1.0


def test_quality_fault_can_reduce_good_throughput_without_flow_queue_growth():
    run = simulate_factory(FactoryConfig(seed=42, units=2500), "fixture_wear_temp")
    out = build_ie_overview(run.records, run.activation_unit)
    assert out["flow"]["post"]["good_throughput_units_per_hour"] < out["flow"]["post"]["throughput_units_per_hour"]
    assert out["queueing"]["post"]["mean_wait_s"] < 5.0


def test_ie_engine_declares_no_ground_truth_dependency():
    run = simulate_factory(FactoryConfig(seed=77, units=900), "gage_measurement_drift")
    out = build_ie_overview(run.records, run.activation_unit)
    assert out["evidence_state"]["ground_truth_dependency"] is False
    serialized = str(out).lower()
    for forbidden in ("measurement_bias_nm", "latent_fault_strength", "true_defect", "root_cause"):
        assert forbidden not in serialized
