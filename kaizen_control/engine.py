from __future__ import annotations

from typing import Any

from kaizen_ie import build_ie_overview
from kaizen_investigator import build_investigation_overview
from kaizen_quality import build_quality_overview
from kaizen_simulation import build_simulation_overview

CONTROL_POLICIES: dict[str, dict[str, Any]] = {
    "MACHINE_TORQUE_BIAS": {
        "primary_metric": "torque_error_nm",
        "chart": "I-MR on torque error with pre-intervention limits",
        "verification": "Daily tool-check against a traceable torque standard; stratify by machine and product.",
        "reaction": "Quarantine affected machine output, verify tool calibration, inspect last conforming check, and escalate if two consecutive checks breach the reaction limit.",
    },
    "GAGE_MEASUREMENT_DRIFT": {
        "primary_metric": "gage torque error / reference-part bias",
        "chart": "reference-part bias trend + scheduled MSA",
        "verification": "Cross-gage reference-part check and periodic bias/linearity verification.",
        "reaction": "Stop disposition decisions from the suspect gage, switch to verified backup measurement, recalibrate and repeat reference study.",
    },
    "FIXTURE_ENVIRONMENT_INTERACTION": {
        "primary_metric": "alignment_measured_mm",
        "chart": "I-MR by fixture with ambient-temperature stratification",
        "verification": "Fixture wear count and alignment check at shift start; monitor temperature interaction.",
        "reaction": "Remove fixture from service, verify locating surfaces and thermal condition, then requalify before release.",
    },
    "SUPPLIER_HUMIDITY_INTERACTION": {
        "primary_metric": "adhesive strength margin",
        "chart": "lot-stratified adhesive-strength trend with humidity overlay",
        "verification": "Incoming-lot containment check and humidity-controlled witness coupons.",
        "reaction": "Hold suspect lot, verify storage/environment, notify supplier quality and release only after acceptance evidence.",
    },
    "CALIBRATION_INTERMITTENT_LOSS": {
        "primary_metric": "calibration_s / upper-tail rate",
        "chart": "service-time tail rate + queue wait trend",
        "verification": "Handshake diagnostic count and calibration-service P95 each shift.",
        "reaction": "Route to backup cell where available, inspect sensor/network handshake, and contain schedule impact until tail behavior returns to baseline.",
    },
    "SEQUENCE_CHANGEOVER_LOSS": {
        "primary_metric": "calibration transition time",
        "chart": "transition-vs-repeat service-time comparison",
        "verification": "Layered process audit of changeover standard work and kit readiness.",
        "reaction": "Stop and restore standard sequence, replenish missing kit/tooling, retrain if repeat deviation is observed.",
    },
}


def build_control_plan(records: list[dict[str, Any]], activation_unit: int, *, line_name: str, seed: int = 0) -> dict[str, Any]:
    inv = build_investigation_overview(records, activation_unit)
    sim = build_simulation_overview(records, activation_unit)
    q = build_quality_overview(records, activation_unit, line_name=line_name, seed=seed)
    ie = build_ie_overview(records, activation_unit)
    top = inv["ranked_hypotheses"][0]
    policy = CONTROL_POLICIES[top["code"]]
    rec = sim["recommended_intervention"]
    spc = q["spc"]["torque_error_imr"]
    pre = records[:activation_unit]
    post = records[activation_unit:]
    pre_def = sum(int(r["observed_defect"]) for r in pre) / max(1, len(pre))
    post_def = sum(int(r["observed_defect"]) for r in post) / max(1, len(post))
    return {
        "version": "control-v1.0",
        "state": "CONTROL_PLAN_READY",
        "basis": {
            "leading_hypothesis": top["code"],
            "target": top["target"],
            "evidence_score": top["evidence_score"],
            "recommended_intervention": rec["label"],
            "causal_status": "NOT_CONFIRMED_BY_OBSERVATION",
        },
        "monitoring": {
            **policy,
            "baseline_limits": {
                "torque_error_center": round(float(spc["center"]), 6),
                "torque_error_ucl": round(float(spc["ucl"]), 6),
                "torque_error_lcl": round(float(spc["lcl"]), 6),
                "policy": q["spc"]["baseline_policy"],
            },
            "cadence": "Review each shift during stabilization; reduce frequency only after sustained evidence of control.",
            "owner_role": "Process/quality engineer with operations supervisor approval",
        },
        "benefits_verification": {
            "minimum_stabilization_window_units": 500,
            "baseline": {
                "pre_defect_rate": round(pre_def, 6),
                "current_post_defect_rate": round(post_def, 6),
                "current_good_throughput_uph": ie["flow"]["post"]["good_throughput_units_per_hour"],
                "current_copq_per_1000_usd": q["pareto_copq"]["copq"]["per_1000_units_usd"],
            },
            "modeled_target": {
                "defect_rate": rec["counterfactual"]["defect_rate"],
                "good_throughput_uph": rec["counterfactual"]["good_throughput_units_per_hour"],
                "copq_per_1000_usd": rec["counterfactual"]["copq_per_1000_units_usd"],
            },
            "success_policy": "After an approved intervention, compare the stabilization window against both the pre-intervention baseline and the predeclared modeled target. Do not claim realized savings until observed post-intervention data support them.",
            "reopen_policy": "If the primary metric remains unstable, capability fails to improve, or realized benefit materially misses the predeclared target, reopen ANALYZE and revise the intervention hypothesis.",
        },
        "handoff": {
            "control_plan_is_causal_proof": False,
            "realized_benefits_verified": False,
            "note": "This is a deterministic control-plan recommendation. It does not fabricate future measurements or realized savings.",
        },
    }
