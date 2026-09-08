from __future__ import annotations

import copy
import hashlib
import math
import random
import statistics
from datetime import datetime, timedelta
from typing import Any

import numpy as np

from kaizen_factory.simulator import PRODUCTS
from kaizen_ie.flow import phase_flow_metrics
from kaizen_ie.queueing import calibration_queue_metrics
from kaizen_investigator import build_investigation_overview

ADHESIVE_LSL = {k: float(v["adhesive_min"]) for k, v in PRODUCTS.items()}

INTERVENTION_CATALOG: dict[str, dict[str, Any]] = {
    "TOOL_RECALIBRATION": {
        "label": "Recalibrate torque tool",
        "hypothesis_code": "MACHINE_TORQUE_BIAS",
        "one_time_cost_usd": 1250.0,
        "planned_downtime_hours": 1.5,
        "description": "Remove the estimated machine-specific torque offset while preserving observed mix and residual variation.",
    },
    "GAGE_RECALIBRATION": {
        "label": "Recalibrate inspection gage",
        "hypothesis_code": "GAGE_MEASUREMENT_DRIFT",
        "one_time_cost_usd": 800.0,
        "planned_downtime_hours": 1.0,
        "description": "Remove the estimated gage-specific measurement offset; physical process settings are not changed.",
    },
    "FIXTURE_REPLACEMENT_THERMAL": {
        "label": "Replace fixture + thermal stabilization",
        "hypothesis_code": "FIXTURE_ENVIRONMENT_INTERACTION",
        "one_time_cost_usd": 9800.0,
        "planned_downtime_hours": 3.5,
        "description": "Restore the suspect fixture toward its pre-incident alignment/torque behavior and attenuate excess thermal sensitivity.",
    },
    "SUPPLIER_CONTAINMENT": {
        "label": "Contain suspect resin lot + humidity control",
        "hypothesis_code": "SUPPLIER_HUMIDITY_INTERACTION",
        "one_time_cost_usd": 6500.0,
        "planned_downtime_hours": 2.0,
        "description": "Restore the suspect lot's adhesive margin toward its pre-incident/control relationship without altering unrelated suppliers.",
    },
    "CALIBRATION_SENSOR_SERVICE": {
        "label": "Service calibration sensor handshake",
        "hypothesis_code": "CALIBRATION_INTERMITTENT_LOSS",
        "one_time_cost_usd": 4800.0,
        "planned_downtime_hours": 2.5,
        "description": "Remove post-incident excess calibration service-time tails relative to product-specific pre-incident baselines.",
    },
    "CHANGEOVER_STANDARD_WORK": {
        "label": "Restore changeover standard work / kit layout",
        "hypothesis_code": "SEQUENCE_CHANGEOVER_LOSS",
        "one_time_cost_usd": 3200.0,
        "planned_downtime_hours": 4.0,
        "description": "Remove excess calibration setup time that appears only on product transitions.",
    },
}

HYPOTHESIS_TO_INTERVENTION = {v["hypothesis_code"]: k for k, v in INTERVENTION_CATALOG.items()}


def _mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def _sd(values: list[float]) -> float:
    return statistics.stdev(values) if len(values) >= 2 else 0.0


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    xs = sorted(float(x) for x in values)
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * q
    lo = int(math.floor(pos)); hi = int(math.ceil(pos))
    if lo == hi:
        return xs[lo]
    frac = pos - lo
    return xs[lo] * (1 - frac) + xs[hi] * frac


def _torque_error(row: dict[str, Any]) -> float:
    return float(row["torque_measured_nm"]) - float(row["torque_target_nm"])


def _adhesive_margin(row: dict[str, Any]) -> float:
    return float(row["adhesive_strength_measured_mpa"]) - ADHESIVE_LSL[str(row["product_variant"])]


def _did_shift(records: list[dict[str, Any]], activation_unit: int, factor: str, target: str, outcome) -> float:
    pre = records[:activation_unit]; post = records[activation_unit:]
    pre_t = [outcome(r) for r in pre if str(r[factor]) == target]
    post_t = [outcome(r) for r in post if str(r[factor]) == target]
    pre_c = [outcome(r) for r in pre if str(r[factor]) != target]
    post_c = [outcome(r) for r in post if str(r[factor]) != target]
    if not pre_t or not post_t or not pre_c or not post_c:
        return 0.0
    return (_mean(post_t) - _mean(pre_t)) - (_mean(post_c) - _mean(pre_c))


def _fit_slope(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 8 or len(set(round(x, 6) for x in xs)) < 3:
        return 0.0
    try:
        return float(np.polyfit(np.asarray(xs, dtype=float), np.asarray(ys, dtype=float), 1)[0])
    except Exception:
        return 0.0


def _hypothesis_map(records: list[dict[str, Any]], activation_unit: int) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    inv = build_investigation_overview(records, activation_unit)
    return {h["code"]: h for h in inv["ranked_hypotheses"]}, inv


def _recompute_defect(row: dict[str, Any]) -> None:
    target = float(row["torque_target_nm"])
    product = str(row["product_variant"])
    torque_fail = abs(float(row["torque_measured_nm"]) - target) > 1.35
    alignment_fail = abs(float(row["alignment_measured_mm"])) > 0.20
    adhesive_fail = float(row["adhesive_strength_measured_mpa"]) < ADHESIVE_LSL[product]
    types: list[str] = []
    if torque_fail: types.append("TORQUE")
    if alignment_fail: types.append("ALIGNMENT")
    if adhesive_fail: types.append("ADHESIVE")
    defect = bool(types)
    original_rework = bool(row.get("rework", False))
    original_scrap = bool(row.get("scrap", False))
    row["observed_defect"] = defect
    row["defect_type"] = "+".join(types) if types else "NONE"
    if not defect:
        row["rework"] = False; row["scrap"] = False
    elif original_rework or original_scrap:
        row["rework"] = original_rework; row["scrap"] = original_scrap
    else:
        row["rework"] = True; row["scrap"] = False


def _apply_intervention(
    records: list[dict[str, Any]],
    activation_unit: int,
    intervention_code: str,
    effectiveness: float,
    hypothesis: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = copy.deepcopy(records)
    target = str(hypothesis.get("target", ""))
    post = rows[activation_unit:]
    estimates: dict[str, Any] = {"target": target, "effectiveness": effectiveness}

    if intervention_code == "TOOL_RECALIBRATION":
        shift = _did_shift(records, activation_unit, "machine_id", target, _torque_error)
        estimates["estimated_torque_bias_nm"] = round(shift, 6)
        for r in post:
            if str(r["machine_id"]) == target:
                r["torque_measured_nm"] = float(r["torque_measured_nm"]) - effectiveness * shift
                _recompute_defect(r)

    elif intervention_code == "GAGE_RECALIBRATION":
        shift = _did_shift(records, activation_unit, "gage_id", target, _torque_error)
        estimates["estimated_measurement_bias_nm"] = round(shift, 6)
        for r in post:
            if str(r["gage_id"]) == target:
                r["torque_measured_nm"] = float(r["torque_measured_nm"]) - effectiveness * shift
                _recompute_defect(r)

    elif intervention_code == "FIXTURE_REPLACEMENT_THERMAL":
        torque_shift = _did_shift(records, activation_unit, "fixture_id", target, _torque_error)
        align_shift = _did_shift(records, activation_unit, "fixture_id", target, lambda r: float(r["alignment_measured_mm"]))
        pre_target = [r for r in records[:activation_unit] if str(r["fixture_id"]) == target]
        post_target = [r for r in records[activation_unit:] if str(r["fixture_id"]) == target]
        pre_slope = _fit_slope([float(r["ambient_temp_c"]) for r in pre_target], [_torque_error(r) for r in pre_target])
        post_slope = _fit_slope([float(r["ambient_temp_c"]) for r in post_target], [_torque_error(r) for r in post_target])
        slope_delta = post_slope - pre_slope
        temp_center = _mean([float(r["ambient_temp_c"]) for r in post_target])
        pre_sd = _sd([_torque_error(r) for r in pre_target])
        post_mean = _mean([_torque_error(r) for r in post_target])
        estimates.update({
            "estimated_torque_shift_nm": round(torque_shift, 6),
            "estimated_alignment_shift_mm": round(align_shift, 6),
            "estimated_excess_temp_slope_nm_per_c": round(slope_delta, 6),
        })
        for r in post:
            if str(r["fixture_id"]) != target:
                continue
            original_error = _torque_error(r)
            thermal_excess = slope_delta * (float(r["ambient_temp_c"]) - temp_center)
            corrected = original_error - effectiveness * (torque_shift + thermal_excess)
            # A replacement also partially restores excess spread toward pre-incident fixture spread.
            if pre_sd > 0:
                corrected = (1 - 0.25 * effectiveness) * corrected + (0.25 * effectiveness) * max(-2.5*pre_sd, min(2.5*pre_sd, corrected))
            r["torque_measured_nm"] = float(r["torque_target_nm"]) + corrected
            r["alignment_measured_mm"] = float(r["alignment_measured_mm"]) - effectiveness * align_shift
            _recompute_defect(r)

    elif intervention_code == "SUPPLIER_CONTAINMENT":
        # Target can be an exact lot. If the investigator returns an S2 prefix-like target,
        # the same startswith policy is used for the counterfactual.
        def is_target(r: dict[str, Any]) -> bool:
            lot = str(r["supplier_lot"])
            return lot == target or (target.endswith("*") and lot.startswith(target[:-1])) or (target.startswith("S2-") and lot == target)
        pre_t = [r for r in records[:activation_unit] if str(r["supplier"]) == "S2"]
        post_t = [r for r in records[activation_unit:] if is_target(r)]
        pre_c = [r for r in records[:activation_unit] if str(r["supplier"]) != "S2"]
        post_c = [r for r in records[activation_unit:] if not is_target(r)]
        shift = ((_mean([_adhesive_margin(r) for r in post_t]) - _mean([_adhesive_margin(r) for r in pre_t]))
                 - (_mean([_adhesive_margin(r) for r in post_c]) - _mean([_adhesive_margin(r) for r in pre_c]))) if pre_t and post_t and pre_c and post_c else 0.0
        pre_slope = _fit_slope([float(r["humidity_pct"]) for r in pre_t], [_adhesive_margin(r) for r in pre_t])
        post_slope = _fit_slope([float(r["humidity_pct"]) for r in post_t], [_adhesive_margin(r) for r in post_t])
        slope_delta = post_slope - pre_slope
        hum_center = _mean([float(r["humidity_pct"]) for r in post_t])
        estimates.update({"estimated_adhesive_margin_shift_mpa": round(shift, 6), "estimated_excess_humidity_slope": round(slope_delta, 6)})
        for r in post:
            if not is_target(r):
                continue
            correction = shift + slope_delta * (float(r["humidity_pct"]) - hum_center)
            # Negative estimated margin shift should be removed (add strength).
            r["adhesive_strength_measured_mpa"] = float(r["adhesive_strength_measured_mpa"]) - effectiveness * correction
            _recompute_defect(r)

    elif intervention_code == "CALIBRATION_SENSOR_SERVICE":
        pre = records[:activation_unit]
        baselines: dict[str, float] = {}
        for product in PRODUCTS:
            vals = [float(r["calibration_s"]) for r in pre if str(r["product_variant"]) == product]
            baselines[product] = _percentile(vals, 0.90)
        estimates["product_specific_pre_p90_s"] = {k: round(v, 4) for k, v in baselines.items()}
        affected = 0
        removed = 0.0
        for r in post:
            base = baselines[str(r["product_variant"])]
            excess = max(0.0, float(r["calibration_s"]) - base)
            if excess > 0:
                r["calibration_s"] = float(r["calibration_s"]) - effectiveness * excess
                affected += 1; removed += effectiveness * excess
        estimates.update({"units_with_excess_tail": affected, "total_service_seconds_removed": round(removed, 3)})

    elif intervention_code == "CHANGEOVER_STANDARD_WORK":
        pre = records[:activation_unit]
        # Product transition state is reconstructed strictly from observable sequence.
        pre_trans: list[float] = []
        prev = None
        for r in pre:
            trans = prev is not None and str(r["product_variant"]) != prev
            if trans: pre_trans.append(float(r["calibration_s"]))
            prev = str(r["product_variant"])
        baseline = _mean(pre_trans) if pre_trans else _mean([float(r["calibration_s"]) for r in pre])
        estimates["pre_transition_mean_calibration_s"] = round(baseline, 4)
        prev = str(records[activation_unit - 1]["product_variant"])
        affected = 0; removed = 0.0
        for r in post:
            trans = str(r["product_variant"]) != prev
            if trans:
                excess = max(0.0, float(r["calibration_s"]) - baseline)
                r["calibration_s"] = float(r["calibration_s"]) - effectiveness * excess
                if excess > 0:
                    affected += 1; removed += effectiveness * excess
            prev = str(r["product_variant"])
        estimates.update({"transition_units_adjusted": affected, "total_setup_seconds_removed": round(removed, 3)})
    else:
        raise ValueError(f"Unknown intervention: {intervention_code}")

    return rows, estimates


def _replay_queue_and_demand(records: list[dict[str, Any]], activation_unit: int, demand_multiplier: float) -> list[dict[str, Any]]:
    rows = copy.deepcopy(records)
    origin = datetime.fromisoformat(rows[0]["timestamp"])
    activation_ts = datetime.fromisoformat(rows[activation_unit]["timestamp"])
    activation_launch_s = (activation_ts - origin).total_seconds()
    calibration_available_s = 0.0
    for i, r in enumerate(rows):
        original_launch_s = (datetime.fromisoformat(r["timestamp"]) - origin).total_seconds()
        if i >= activation_unit:
            launch_s = activation_launch_s + (original_launch_s - activation_launch_s) / demand_multiplier
        else:
            launch_s = original_launch_s
        r["timestamp"] = (origin + timedelta(seconds=launch_s)).isoformat()
        upstream = sum(float(r[c]) for c in ("bearing_press_s", "motor_assembly_s", "adhesive_dispense_s", "torque_fastening_s"))
        arrival = launch_s + upstream
        start = max(arrival, calibration_available_s)
        wait = max(0.0, start - arrival)
        calibration_available_s = start + float(r["calibration_s"])
        r["queue_wait_s"] = round(wait, 4)
        r["total_processing_s"] = round(sum(float(r[c]) for c in (
            "bearing_press_s", "motor_assembly_s", "adhesive_dispense_s", "torque_fastening_s",
            "calibration_s", "functional_test_s", "final_inspection_s"
        )), 4)
        _recompute_defect(r)
        quality_cost = (46.0 if r["rework"] else 0.0) + (215.0 if r["scrap"] else 0.0)
        flow_cost = min(18.0, wait * 0.025) if wait > 60 else 0.0
        r["copq_usd"] = round(quality_cost + flow_cost, 2)
    return rows


def _cpk_torque(rows: list[dict[str, Any]]) -> float | None:
    errors = [_torque_error(r) for r in rows]
    if len(errors) < 2:
        return None
    m = _mean(errors); s = _sd(errors)
    if s <= 1e-12:
        return None
    return min((1.35 - m) / (3*s), (m + 1.35) / (3*s))


def _metrics(rows: list[dict[str, Any]], activation_unit: int) -> dict[str, Any]:
    post = rows[activation_unit:]
    flow = phase_flow_metrics(post, phase="post")
    queue = calibration_queue_metrics(post, phase="post")
    n = max(1, len(post))
    defects = sum(int(r["observed_defect"]) for r in post)
    copq_total = sum(float(r["copq_usd"]) for r in post)
    service_mean = _mean([float(r["calibration_s"]) for r in post])
    return {
        "n": len(post),
        "defect_rate": round(defects/n, 6),
        "first_pass_yield": round(1-defects/n, 6),
        "throughput_units_per_hour": flow["throughput_units_per_hour"],
        "good_throughput_units_per_hour": flow["good_throughput_units_per_hour"],
        "mean_lead_time_s": flow["mean_flow_time_s"],
        "mean_queue_wait_s": queue["mean_wait_s"],
        "p95_queue_wait_s": flow["p95_queue_wait_s"],
        "average_wip_units": flow["average_wip_units"],
        "max_wip_units": flow["max_wip_units"],
        "calibration_service_rate_units_per_hour": round(3600/service_mean, 4) if service_mean else 0.0,
        "copq_total_usd": round(copq_total, 2),
        "copq_per_1000_units_usd": round(copq_total/n*1000, 2),
        "torque_cpk": round(_cpk_torque(post), 4) if _cpk_torque(post) is not None else None,
        "little_law_error_pct": flow["little_law_error_pct"],
    }


def _delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    return {
        "defect_rate_pp": round((after["defect_rate"] - before["defect_rate"]) * 100, 4),
        "good_throughput_units_per_hour": round(after["good_throughput_units_per_hour"] - before["good_throughput_units_per_hour"], 4),
        "mean_lead_time_s": round(after["mean_lead_time_s"] - before["mean_lead_time_s"], 4),
        "mean_queue_wait_s": round(after["mean_queue_wait_s"] - before["mean_queue_wait_s"], 4),
        "average_wip_units": round(after["average_wip_units"] - before["average_wip_units"], 4),
        "copq_per_1000_units_usd": round(after["copq_per_1000_units_usd"] - before["copq_per_1000_units_usd"], 2),
        "torque_cpk": None if before["torque_cpk"] is None or after["torque_cpk"] is None else round(after["torque_cpk"] - before["torque_cpk"], 4),
    }


def _paired_bootstrap(before_rows: list[dict[str, Any]], after_rows: list[dict[str, Any]], activation_unit: int, *, seed: int, reps: int = 250) -> dict[str, Any]:
    b = before_rows[activation_unit:]; a = after_rows[activation_unit:]
    n = min(len(b), len(a))
    if n < 30:
        return {"repetitions": 0, "status": "INSUFFICIENT_ROWS"}
    diffs_defect = [float(a[i]["observed_defect"]) - float(b[i]["observed_defect"]) for i in range(n)]
    diffs_copq = [(float(a[i]["copq_usd"]) - float(b[i]["copq_usd"])) * 1000.0 for i in range(n)]
    diffs_flow = [(float(a[i]["total_processing_s"]) + float(a[i]["queue_wait_s"])) - (float(b[i]["total_processing_s"]) + float(b[i]["queue_wait_s"])) for i in range(n)]
    rng = random.Random(seed)
    defect_stats: list[float] = []; copq_stats: list[float] = []; flow_stats: list[float] = []
    for _ in range(reps):
        idx = [rng.randrange(n) for _ in range(n)]
        defect_stats.append(_mean([diffs_defect[i] for i in idx]) * 100.0)
        # each unit's COPQ diff converted to per-1000; average preserves scale after /n
        copq_stats.append(_mean([diffs_copq[i] for i in idx]))
        flow_stats.append(_mean([diffs_flow[i] for i in idx]))
    return {
        "repetitions": reps,
        "method": "paired unit bootstrap; 90% interval; deterministic seed",
        "defect_rate_pp_delta_90pct": [round(_percentile(defect_stats,0.05),4), round(_percentile(defect_stats,0.95),4)],
        "copq_per_1000_delta_usd_90pct": [round(_percentile(copq_stats,0.05),2), round(_percentile(copq_stats,0.95),2)],
        "mean_unit_flow_time_delta_s_90pct": [round(_percentile(flow_stats,0.05),4), round(_percentile(flow_stats,0.95),4)],
    }


def _stable_seed(intervention_code: str, records: list[dict[str, Any]]) -> int:
    token = f"{intervention_code}|{len(records)}|{records[0]['unit_id']}|{records[-1]['unit_id']}"
    return int(hashlib.sha256(token.encode()).hexdigest()[:8], 16)


def _run_with_context(
    records: list[dict[str, Any]],
    activation_unit: int,
    intervention_code: str,
    *,
    effectiveness: float,
    demand_multiplier: float,
    hmap: dict[str, dict[str, Any]],
    inv: dict[str, Any],
    bootstrap: bool,
) -> dict[str, Any]:
    meta = INTERVENTION_CATALOG[intervention_code]
    hyp = hmap[meta["hypothesis_code"]]
    baseline_rows = _replay_queue_and_demand(records, activation_unit, demand_multiplier)
    modified, estimates = _apply_intervention(records, activation_unit, intervention_code, effectiveness, hyp)
    counterfactual_rows = _replay_queue_and_demand(modified, activation_unit, demand_multiplier)
    before = _metrics(baseline_rows, activation_unit)
    after = _metrics(counterfactual_rows, activation_unit)
    delta = _delta(before, after)
    boot = (_paired_bootstrap(
        baseline_rows, counterfactual_rows, activation_unit,
        seed=_stable_seed(intervention_code, records)
    ) if bootstrap else {"repetitions": 0, "status": "OMITTED_FOR_CANDIDATE_SCREEN"})
    savings = -delta["copq_per_1000_units_usd"]
    cost = float(meta["one_time_cost_usd"])
    payback_units = None if savings <= 0 else cost / savings * 1000.0
    return {
        "intervention_code": intervention_code,
        "label": meta["label"],
        "description": meta["description"],
        "diagnostic_basis": {
            "hypothesis_code": hyp["code"],
            "target": hyp["target"],
            "evidence_score": hyp["evidence_score"],
            "status": hyp["status"],
            "causal_status": hyp["causal_status"],
        },
        "settings": {"effectiveness": effectiveness, "demand_multiplier": demand_multiplier},
        "engineering_assumptions": {
            "one_time_cost_usd": cost,
            "planned_downtime_hours": meta["planned_downtime_hours"],
            "cost_source": "synthetic portfolio assumption; replace with plant financial data in deployment",
        },
        "estimated_intervention_parameters": estimates,
        "baseline": before,
        "counterfactual": after,
        "delta": delta,
        "uncertainty": boot,
        "simple_payback_units": None if payback_units is None else round(payback_units, 0),
        "paired_replay_policy": "Identical observed unit mix and deterministic arrival path are replayed at the selected demand multiplier. Only the chosen intervention transformation changes.",
        "causal_guardrail": "Simulation estimates consequences conditional on the observational hypothesis and intervention model. It does not unlock causal confirmation or DOE evidence.",
        "ground_truth_dependency": False,
        "investigator_top_code": inv["top_suspect"]["code"],
    }


def run_what_if(
    records: list[dict[str, Any]],
    activation_unit: int,
    intervention_code: str,
    *,
    effectiveness: float = 1.0,
    demand_multiplier: float = 1.0,
) -> dict[str, Any]:
    if intervention_code not in INTERVENTION_CATALOG:
        raise ValueError(f"Unknown intervention: {intervention_code}")
    if not 0.0 <= effectiveness <= 1.0:
        raise ValueError("effectiveness must be between 0 and 1")
    if not 0.5 <= demand_multiplier <= 1.75:
        raise ValueError("demand_multiplier must be between 0.5 and 1.75")
    hmap, inv = _hypothesis_map(records, activation_unit)
    return _run_with_context(
        records, activation_unit, intervention_code,
        effectiveness=effectiveness, demand_multiplier=demand_multiplier,
        hmap=hmap, inv=inv, bootstrap=True,
    )

def build_simulation_overview(records: list[dict[str, Any]], activation_unit: int) -> dict[str, Any]:
    hmap, inv = _hypothesis_map(records, activation_unit)
    top_code = inv["top_suspect"]["code"]
    recommended = HYPOTHESIS_TO_INTERVENTION[top_code]
    candidates: list[dict[str, Any]] = []
    cached: dict[str, dict[str, Any]] = {}
    for code, meta in INTERVENTION_CATALOG.items():
        result = _run_with_context(
            records, activation_unit, code,
            effectiveness=1.0, demand_multiplier=1.0,
            hmap=hmap, inv=inv, bootstrap=False,
        )
        cached[code] = result
        candidates.append({
            "intervention_code": code,
            "label": meta["label"],
            "hypothesis_code": meta["hypothesis_code"],
            "target": result["diagnostic_basis"]["target"],
            "evidence_score": result["diagnostic_basis"]["evidence_score"],
            "recommended_for_top_suspect": code == recommended,
            "defect_rate_pp_delta": result["delta"]["defect_rate_pp"],
            "good_throughput_delta_uph": result["delta"]["good_throughput_units_per_hour"],
            "lead_time_delta_s": result["delta"]["mean_lead_time_s"],
            "queue_wait_delta_s": result["delta"]["mean_queue_wait_s"],
            "copq_per_1000_delta_usd": result["delta"]["copq_per_1000_units_usd"],
            "one_time_cost_usd": result["engineering_assumptions"]["one_time_cost_usd"],
            "planned_downtime_hours": result["engineering_assumptions"]["planned_downtime_hours"],
            "simple_payback_units": result["simple_payback_units"],
        })
    # Only the recommended default receives the costlier uncertainty calculation on page load.
    recommended_result = _run_with_context(
        records, activation_unit, recommended,
        effectiveness=1.0, demand_multiplier=1.0,
        hmap=hmap, inv=inv, bootstrap=True,
    )
    return {
        "version": "simulation-v0.6",
        "mode": "PAIRED_COUNTERFACTUAL_REPLAY",
        "recommended_intervention_code": recommended,
        "recommended_intervention": recommended_result,
        "candidate_interventions": candidates,
        "controls": {
            "effectiveness_range": [0.0, 1.0],
            "demand_multiplier_range": [0.5, 1.75],
            "available_interventions": [
                {"code": code, "label": meta["label"], "description": meta["description"]}
                for code, meta in INTERVENTION_CATALOG.items()
            ],
        },
        "evidence_state": {
            "simulation_core": "IMPLEMENTED_AND_TESTED",
            "ground_truth_dependency": False,
            "causal_confirmation_unlocked": False,
            "note": "V0.6 performs paired counterfactual replay from observable records and the statistical diagnosis. It is decision support, not experimental proof.",
        },
    }



def run_portfolio(
    records: list[dict[str, Any]],
    activation_unit: int,
    intervention_codes: list[str],
    *,
    effectiveness: float = 1.0,
    demand_multiplier: float = 1.0,
    bootstrap: bool = True,
    _hmap: dict[str, dict[str, Any]] | None = None,
    _inv: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Replay a deterministic multi-intervention portfolio.

    Interventions are applied in a canonical catalog order so portfolio results are reproducible.
    Each intervention is re-estimated against the current modeled state; this deliberately allows
    overlapping interventions to exhibit diminishing/interactive effects instead of assuming
    additive KPI deltas. Sealed simulator truth is never supplied.
    """
    if not 0.0 <= effectiveness <= 1.0:
        raise ValueError("effectiveness must be between 0 and 1")
    if not 0.5 <= demand_multiplier <= 1.75:
        raise ValueError("demand_multiplier must be between 0.5 and 1.75")
    unique = []
    seen = set()
    for code in intervention_codes:
        if code not in INTERVENTION_CATALOG:
            raise ValueError(f"Unknown intervention: {code}")
        if code not in seen:
            seen.add(code); unique.append(code)
    ordered = [code for code in INTERVENTION_CATALOG if code in seen]

    hmap, inv = (_hmap, _inv) if _hmap is not None and _inv is not None else _hypothesis_map(records, activation_unit)
    baseline_rows = _replay_queue_and_demand(records, activation_unit, demand_multiplier)
    working = copy.deepcopy(records)
    estimates: list[dict[str, Any]] = []
    for code in ordered:
        meta = INTERVENTION_CATALOG[code]
        hyp = hmap[meta["hypothesis_code"]]
        working, est = _apply_intervention(working, activation_unit, code, effectiveness, hyp)
        estimates.append({"intervention_code": code, "target": hyp["target"], "parameters": est})
    counterfactual_rows = _replay_queue_and_demand(working, activation_unit, demand_multiplier)
    before = _metrics(baseline_rows, activation_unit)
    after = _metrics(counterfactual_rows, activation_unit)
    delta = _delta(before, after)
    total_cost = sum(float(INTERVENTION_CATALOG[c]["one_time_cost_usd"]) for c in ordered)
    total_downtime = sum(float(INTERVENTION_CATALOG[c]["planned_downtime_hours"]) for c in ordered)
    boot = (_paired_bootstrap(
        baseline_rows, counterfactual_rows, activation_unit,
        seed=_stable_seed("PORTFOLIO:" + "+".join(ordered or ["NONE"]), records)
    ) if bootstrap else {"repetitions": 0, "status": "OMITTED_FOR_SEARCH"})
    return {
        "intervention_codes": ordered,
        "interventions": [
            {
                "code": c,
                "label": INTERVENTION_CATALOG[c]["label"],
                "cost_usd": INTERVENTION_CATALOG[c]["one_time_cost_usd"],
                "downtime_hours": INTERVENTION_CATALOG[c]["planned_downtime_hours"],
                "hypothesis_code": INTERVENTION_CATALOG[c]["hypothesis_code"],
                "target": hmap[INTERVENTION_CATALOG[c]["hypothesis_code"]]["target"],
                "evidence_score": hmap[INTERVENTION_CATALOG[c]["hypothesis_code"]]["evidence_score"],
            }
            for c in ordered
        ],
        "settings": {"effectiveness": effectiveness, "demand_multiplier": demand_multiplier},
        "engineering_assumptions": {
            "total_one_time_cost_usd": round(total_cost, 2),
            "total_planned_downtime_hours": round(total_downtime, 3),
            "combination_order": ordered,
            "portfolio_replay_policy": "Canonical catalog order; each action is re-estimated against the current modeled counterfactual state to avoid simple additive KPI assumptions.",
        },
        "estimated_intervention_parameters": estimates,
        "baseline": before,
        "counterfactual": after,
        "delta": delta,
        "uncertainty": boot,
        "ground_truth_dependency": False,
        "causal_guardrail": "Portfolio replay is conditional decision support. It does not convert observational diagnosis into causal confirmation or DOE evidence.",
        "investigator_top_code": inv["top_suspect"]["code"],
    }
