from __future__ import annotations

import math
import random
import statistics
import uuid
from collections import Counter
from datetime import datetime, timedelta
from typing import Any

from .models import FactoryConfig, SimulationResult
from .scenarios import FAULT_CATALOG, get_scenario

PRODUCTS = {
    "A": {"torque_target": 18.0, "adhesive_min": 5.4, "calibration_s": 32.0, "mix": 0.50},
    "B": {"torque_target": 20.0, "adhesive_min": 5.7, "calibration_s": 35.0, "mix": 0.30},
    "C": {"torque_target": 22.0, "adhesive_min": 6.0, "calibration_s": 40.0, "mix": 0.20},
}

OPERATORS = ["O1", "O2", "O3", "O4", "O5", "O6"]
FIXTURES = ["F1", "F2", "F3", "F4"]
MACHINES = ["M1", "M2"]
GAGES = ["G1", "G2"]
SUPPLIERS = ["S1", "S2", "S3"]

STATION_BASE = {
    "bearing_press_s": 24.0,
    "motor_assembly_s": 31.0,
    "adhesive_dispense_s": 27.0,
    "torque_fastening_s": 29.0,
    "functional_test_s": 30.0,
    "final_inspection_s": 21.0,
}

# The production investigator is allowed to see only keys in observable records.
# Latent physical values and fault-strength variables are stored separately.
OBSERVABLE_SCHEMA_VERSION = "factory-observable-v1"
LATENT_SCHEMA_VERSION = "factory-latent-v1"


def _weighted_choice(rng: random.Random, values: list[str], weights: list[float]) -> str:
    return rng.choices(values, weights=weights, k=1)[0]


def _shift_for_time(ts: datetime) -> int:
    if 6 <= ts.hour < 14:
        return 1
    if 14 <= ts.hour < 22:
        return 2
    return 3


def _operator_for(shift: int, i: int) -> str:
    pools = {1: ["O1", "O2", "O3"], 2: ["O2", "O4", "O5"], 3: ["O3", "O5", "O6"]}
    pool = pools[shift]
    return pool[(i // 17) % len(pool)]


def _ambient(i: int, rng: random.Random) -> tuple[float, float]:
    day_phase = 2 * math.pi * ((i % 2057) / 2057)
    temp = 23.0 + 3.2 * math.sin(day_phase - 0.7) + rng.gauss(0, 0.55)
    humidity = 47.0 + 10.0 * math.sin(day_phase + 1.2) + rng.gauss(0, 2.0)
    return round(temp, 3), round(max(25.0, min(75.0, humidity)), 3)


def _station_time(base: float, rng: random.Random, cv: float = 0.055) -> float:
    return max(base * 0.65, rng.gauss(base, base * cv))


def _public_summary(records: list[dict[str, Any]], activation_unit: int) -> dict[str, Any]:
    def block(rows: list[dict[str, Any]]) -> dict[str, Any]:
        n = max(1, len(rows))
        defects = sum(int(r["observed_defect"]) for r in rows)
        rework = sum(int(r["rework"]) for r in rows)
        return {
            "units": len(rows),
            "observed_defect_rate": round(defects / n, 5),
            "rework_rate": round(rework / n, 5),
            "avg_queue_wait_s": round(statistics.fmean(r["queue_wait_s"] for r in rows), 3) if rows else 0.0,
            "avg_calibration_s": round(statistics.fmean(r["calibration_s"] for r in rows), 3) if rows else 0.0,
            "avg_unit_flow_time_s": round(
                statistics.fmean(r["total_processing_s"] + r["queue_wait_s"] for r in rows), 3
            ) if rows else 0.0,
            "copq_usd": round(sum(r["copq_usd"] for r in rows), 2),
        }

    pre = [r for r in records if r["unit_index"] < activation_unit]
    post = [r for r in records if r["unit_index"] >= activation_unit]
    return {"pre_incident": block(pre), "post_incident": block(post)}


def _latent_summary(latent_records: list[dict[str, Any]], activation_unit: int) -> dict[str, Any]:
    def block(rows: list[dict[str, Any]]) -> dict[str, Any]:
        n = max(1, len(rows))
        return {
            "units": len(rows),
            "true_defect_rate": round(sum(int(r["true_defect"]) for r in rows) / n, 5),
            "mean_fault_strength": round(statistics.fmean(r["latent_fault_strength"] for r in rows), 6)
            if rows else 0.0,
        }

    pre = [r for r in latent_records if r["unit_index"] < activation_unit]
    post = [r for r in latent_records if r["unit_index"] >= activation_unit]
    return {"pre_incident": block(pre), "post_incident": block(post)}


def simulate_factory(config: FactoryConfig, scenario_code: str = "random", *, reveal_truth: bool = False) -> SimulationResult:
    """Generate one blind manufacturing incident.

    ``reveal_truth`` is retained for API compatibility but never changes what is placed in
    observable records. Ground truth always exists in the SimulationResult's sealed store;
    the API boundary decides whether it can be returned to a caller.
    """
    del reveal_truth
    config.validate()
    rng = random.Random(config.seed)
    if scenario_code == "random":
        scenario_code = rng.choice(sorted(FAULT_CATALOG))
    scenario = get_scenario(scenario_code)

    activation_unit = max(1, int(config.units * config.activation_fraction))
    start = datetime.fromisoformat(config.start_time)
    run_id = f"KZN-{uuid.uuid4().hex[:10].upper()}"

    fixture_age = {fixture: rng.randint(120, 450) for fixture in FIXTURES}
    calibration_available_s = 0.0
    prior_variant: str | None = None
    records: list[dict[str, Any]] = []
    latent_records: list[dict[str, Any]] = []

    product_values = list(PRODUCTS)
    product_weights = [PRODUCTS[p]["mix"] for p in product_values]
    shifted_supplier_lot = f"S2-L{(activation_unit // 180) + 100:03d}" if scenario_code == "supplier_resin_shift" else None

    for i in range(config.units):
        launch_s = i * 42.0 + rng.gauss(0, 2.0)
        ts = start + timedelta(seconds=max(0.0, launch_s))
        shift = _shift_for_time(ts)
        product = _weighted_choice(rng, product_values, product_weights)
        product_cfg = PRODUCTS[product]
        operator = _operator_for(shift, i)

        # Deliberate confounding: O3 uses F4 more often; M2 processes more product C.
        fixture = "F4" if operator == "O3" and rng.random() < 0.46 else rng.choice(FIXTURES)
        machine = "M2" if product == "C" and rng.random() < 0.66 else rng.choice(MACHINES)
        gage = "G2" if shift == 3 and rng.random() < 0.63 else rng.choice(GAGES)

        lot_block = i // 180
        supplier = SUPPLIERS[lot_block % len(SUPPLIERS)]
        supplier_lot = f"{supplier}-L{100 + lot_block:03d}"
        if scenario_code == "supplier_resin_shift" and i >= activation_unit and (i - activation_unit) % 360 < 190:
            supplier = "S2"
            supplier_lot = shifted_supplier_lot or "S2-L999"

        temp_c, humidity_pct = _ambient(i, rng)
        fixture_age[fixture] += 1

        alignment_actual = rng.gauss(0.0, 0.058)
        torque_bias = {"M1": -0.03, "M2": 0.04}[machine]
        operator_bias = {"O1": 0.02, "O2": -0.02, "O3": 0.05, "O4": 0.0, "O5": -0.04, "O6": 0.03}[operator]
        torque_actual = product_cfg["torque_target"] + torque_bias + operator_bias + rng.gauss(0, 0.42)
        adhesive_actual = 6.65 + (0.12 if product == "A" else 0.0) + rng.gauss(0, 0.31)

        active = i >= activation_unit
        latent_fault_strength = 0.0
        latent_components: dict[str, float] = {}
        if active:
            progress = (i - activation_unit) / max(1, config.units - activation_unit - 1)
            if scenario_code == "fixture_wear_temp" and fixture == "F4":
                wear = 0.08 + 0.22 * progress + max(0, fixture_age[fixture] - 650) * 0.00022
                temp_amp = max(0.0, temp_c - 23.5) * 0.055
                alignment_actual += rng.gauss(wear, 0.035)
                torque_actual += (wear * 2.5) + (temp_amp * (1.0 + 3.2 * wear)) + rng.gauss(0, 0.18 + wear * 0.55)
                latent_fault_strength = wear + temp_amp
                latent_components = {"fixture_wear": wear, "temperature_amplification": temp_amp}
            elif scenario_code == "supplier_resin_shift" and supplier_lot == shifted_supplier_lot:
                humidity_penalty = max(0.0, humidity_pct - 48.0) * 0.022
                adhesive_actual -= 0.78 + humidity_penalty + rng.gauss(0, 0.09)
                latent_fault_strength = 0.78 + humidity_penalty
                latent_components = {"resin_shift": 0.78, "humidity_penalty": humidity_penalty}
            elif scenario_code == "tool_calibration_drift" and machine == "M2":
                drift = 0.18 + 1.02 * progress
                torque_actual += drift + rng.gauss(0, 0.09)
                latent_fault_strength = drift
                latent_components = {"tool_bias": drift}

        # Measurement system is distinct from physical truth.
        torque_measured = torque_actual + rng.gauss(0, 0.16)
        alignment_measured = alignment_actual + rng.gauss(0, 0.018)
        adhesive_measured = adhesive_actual + rng.gauss(0, 0.11)
        measurement_bias = 0.0
        if active and scenario_code == "gage_measurement_drift" and gage == "G2":
            progress = (i - activation_unit) / max(1, config.units - activation_unit - 1)
            measurement_bias = 0.38 + 0.92 * progress
            torque_measured += measurement_bias
            latent_fault_strength = measurement_bias
            latent_components = {"gage_zero_bias": measurement_bias}

        bearing_s = _station_time(STATION_BASE["bearing_press_s"], rng)
        motor_s = _station_time(STATION_BASE["motor_assembly_s"], rng)
        adhesive_s = _station_time(STATION_BASE["adhesive_dispense_s"], rng)
        torque_s = _station_time(STATION_BASE["torque_fastening_s"], rng)
        calibration_s = _station_time(product_cfg["calibration_s"], rng, 0.06)
        functional_s = _station_time(STATION_BASE["functional_test_s"], rng)
        inspection_s = _station_time(STATION_BASE["final_inspection_s"], rng)

        microstop_s = 0.0
        changeover_extra_s = 0.0
        if active and scenario_code == "calibration_microstops" and rng.random() < 0.20:
            microstop_s = rng.uniform(18.0, 45.0)
            calibration_s += microstop_s
            latent_fault_strength = microstop_s
            latent_components = {"microstop_delay_s": microstop_s}
        if active and scenario_code == "changeover_deterioration" and prior_variant is not None and product != prior_variant:
            changeover_extra_s = rng.uniform(8.0, 22.0)
            calibration_s += changeover_extra_s
            latent_fault_strength = changeover_extra_s
            latent_components = {"excess_changeover_s": changeover_extra_s}

        upstream_to_cal_s = bearing_s + motor_s + adhesive_s + torque_s
        calibration_arrival_s = launch_s + upstream_to_cal_s
        calibration_start_s = max(calibration_arrival_s, calibration_available_s)
        queue_wait_s = max(0.0, calibration_start_s - calibration_arrival_s)
        calibration_available_s = calibration_start_s + calibration_s

        target = product_cfg["torque_target"]
        torque_true_fail = abs(torque_actual - target) > 1.35
        alignment_true_fail = abs(alignment_actual) > 0.20
        adhesive_true_fail = adhesive_actual < product_cfg["adhesive_min"]
        true_defect = torque_true_fail or alignment_true_fail or adhesive_true_fail

        torque_observed_fail = abs(torque_measured - target) > 1.35
        alignment_observed_fail = abs(alignment_measured) > 0.20
        adhesive_observed_fail = adhesive_measured < product_cfg["adhesive_min"]
        observed_defect = torque_observed_fail or alignment_observed_fail or adhesive_observed_fail

        defect_types: list[str] = []
        if torque_observed_fail:
            defect_types.append("TORQUE")
        if alignment_observed_fail:
            defect_types.append("ALIGNMENT")
        if adhesive_observed_fail:
            defect_types.append("ADHESIVE")
        if not defect_types:
            defect_types.append("NONE")

        rework = observed_defect and rng.random() < 0.84
        scrap = observed_defect and not rework
        copq = (46.0 if rework else 0.0) + (215.0 if scrap else 0.0)
        if queue_wait_s > 60:
            copq += min(18.0, queue_wait_s * 0.025)

        total_processing_s = bearing_s + motor_s + adhesive_s + torque_s + calibration_s + functional_s + inspection_s
        unit_id = f"ACT-{i + 1:07d}"
        observable = {
            "unit_index": i,
            "unit_id": unit_id,
            "timestamp": ts.isoformat(),
            "shift": shift,
            "product_variant": product,
            "operator_id": operator,
            "machine_id": machine,
            "fixture_id": fixture,
            "fixture_age_cycles": fixture_age[fixture],
            "gage_id": gage,
            "supplier": supplier,
            "supplier_lot": supplier_lot,
            "ambient_temp_c": temp_c,
            "humidity_pct": humidity_pct,
            "torque_target_nm": target,
            "torque_measured_nm": round(torque_measured, 5),
            "alignment_measured_mm": round(alignment_measured, 5),
            "adhesive_strength_measured_mpa": round(adhesive_measured, 5),
            "bearing_press_s": round(bearing_s, 4),
            "motor_assembly_s": round(motor_s, 4),
            "adhesive_dispense_s": round(adhesive_s, 4),
            "torque_fastening_s": round(torque_s, 4),
            "calibration_s": round(calibration_s, 4),
            "functional_test_s": round(functional_s, 4),
            "final_inspection_s": round(inspection_s, 4),
            "queue_wait_s": round(queue_wait_s, 4),
            "total_processing_s": round(total_processing_s, 4),
            "observed_defect": bool(observed_defect),
            "defect_type": "+".join(defect_types),
            "rework": bool(rework),
            "scrap": bool(scrap),
            "copq_usd": round(copq, 2),
        }
        latent = {
            "unit_index": i,
            "unit_id": unit_id,
            "incident_active": active,
            "torque_actual_nm": round(torque_actual, 6),
            "alignment_actual_mm": round(alignment_actual, 6),
            "adhesive_strength_actual_mpa": round(adhesive_actual, 6),
            "measurement_bias_nm": round(measurement_bias, 6),
            "microstop_s": round(microstop_s, 6),
            "changeover_extra_s": round(changeover_extra_s, 6),
            "true_defect": bool(true_defect),
            "latent_fault_strength": round(latent_fault_strength, 6),
            "latent_components": latent_components,
        }
        records.append(observable)
        latent_records.append(latent)
        prior_variant = product

    summary = _public_summary(records, activation_unit)
    latent_summary = _latent_summary(latent_records, activation_unit)
    defect_counter = Counter(r["defect_type"] for r in records if r["observed_defect"])
    public_summary = {
        **summary,
        "symptom": scenario.public_symptom,
        "affected_step_hint": scenario.affected_step,
        "top_observed_defects": defect_counter.most_common(5),
        "observable_schema": OBSERVABLE_SCHEMA_VERSION,
    }
    truth = {
        "scenario": scenario.truth_dict(),
        "activation_unit": activation_unit,
        "activation_timestamp": records[activation_unit]["timestamp"],
        "seed": config.seed,
        "latent_schema": LATENT_SCHEMA_VERSION,
        "latent_summary": latent_summary,
        "injection_policy": "deterministic for a fixed seed/configuration/scenario",
        "causal_firewall": {
            "observable_records_contain_latent_values": False,
            "diagnostic_layer_access_before_reveal": "forbidden",
            "sealed_record_count": len(latent_records),
        },
        "validation_note": (
            "Later diagnostic releases must infer the mechanism only from observable records. "
            "Latent records exist solely for benchmark scoring and explicit ground-truth reveal."
        ),
    }
    return SimulationResult(
        run_id=run_id,
        config=config,
        scenario_code=scenario_code,
        activation_unit=activation_unit,
        public_summary=public_summary,
        records=records,
        latent_records=latent_records,
        ground_truth=truth,
    )
