from __future__ import annotations

from typing import Any

from kaizen_investigator import build_investigation_overview


# Ground-truth scoring policy. This table lives exclusively in the arena scoring
# layer and is never passed to the blind investigator. It is consulted only after
# an explicit reveal/score action.
EXPECTED_ATTRIBUTION: dict[str, dict[str, Any]] = {
    "tool_calibration_drift": {
        "code": "MACHINE_TORQUE_BIAS", "target": "M2", "direction": "INCREASE", "interaction": None,
    },
    "fixture_wear_temp": {
        "code": "FIXTURE_ENVIRONMENT_INTERACTION", "target": "F4", "direction": "INCREASE", "interaction": "ambient_temp_c",
    },
    "supplier_resin_shift": {
        "code": "SUPPLIER_HUMIDITY_INTERACTION", "target_prefix": "S2-", "direction": "DECREASE", "interaction": "humidity_pct",
    },
    "gage_measurement_drift": {
        "code": "GAGE_MEASUREMENT_DRIFT", "target": "G2", "direction": "INCREASE", "interaction": None,
    },
    "calibration_microstops": {
        "code": "CALIBRATION_INTERMITTENT_LOSS", "target": "Calibration", "direction": "INCREASE", "interaction": None,
    },
    "changeover_deterioration": {
        "code": "SEQUENCE_CHANGEOVER_LOSS", "target": "Calibration product transitions", "direction": "INCREASE", "interaction": "product_transition",
    },
}


def _target_ok(target: str, expected: dict[str, Any]) -> bool:
    if "target" in expected:
        return target == expected["target"]
    return target.startswith(str(expected.get("target_prefix", "")))


def build_arena_overview(records: list[dict[str, Any]], activation_unit: int) -> dict[str, Any]:
    """Build the blind investigation arena from observable evidence only.

    This function intentionally receives neither scenario code nor ground truth.
    It can therefore be exposed before reveal without weakening the causal firewall.
    """
    inv = build_investigation_overview(records, activation_unit)
    top = inv["top_suspect"]
    attr = top.get("attribution") or {}
    events = [
        {
            "order": 1,
            "stage": "DETECT",
            "title": "Incident boundary established",
            "detail": f"Observable records split at unit {activation_unit:,}; no causal label is available to the investigator.",
            "status": "COMPLETE",
        },
        {
            "order": 2,
            "stage": "MEASURE",
            "title": "Process evidence quantified",
            "detail": "Lean Six Sigma and IE layers establish quality, capability, flow, queueing and capacity changes from observable records.",
            "status": "COMPLETE",
        },
        {
            "order": 3,
            "stage": "HYPOTHESIZE",
            "title": f"{len(inv['ranked_hypotheses'])} competing mechanisms challenged",
            "detail": "Equipment, measurement, fixture/environment, supplier/material, sequence/changeover and intermittent-capacity explanations are scored in parallel.",
            "status": "COMPLETE",
        },
        {
            "order": 4,
            "stage": "ADJUST",
            "title": "Confounders and interactions challenged",
            "detail": f"{inv['adjusted_models']['models_fit']}/{inv['adjusted_models']['models_attempted']} adjusted models fit; operator, shift and product-mix checks remain non-causal competing evidence.",
            "status": "COMPLETE",
        },
        {
            "order": 5,
            "stage": "RANK",
            "title": f"Leading suspect: {top['target']}",
            "detail": f"{top['title']} ranks first at {top['evidence_score']:.1f}/100 with {inv['ambiguity']['level'].lower()} ambiguity. Direction: {attr.get('direction') or 'not identified'}.",
            "status": "COMPLETE",
        },
        {
            "order": 6,
            "stage": "STOP",
            "title": "Causal confirmation intentionally withheld",
            "detail": "The Correlation ≠ Cause gate stops at observational support. Reveal/score is an evaluation action, not evidence used by the investigator.",
            "status": "LOCKED",
        },
    ]
    return {
        "mode": "BLIND_DIAGNOSIS",
        "truth_available_to_investigator": False,
        "prediction_snapshot": {
            "code": top["code"],
            "title": top["title"],
            "target": top["target"],
            "direction": attr.get("direction"),
            "interaction_partner": attr.get("interaction_partner"),
            "evidence_score": top["evidence_score"],
            "status": top["status"],
            "ambiguity": inv["ambiguity"]["level"],
        },
        "timeline": events,
        "scoring_dimensions": [
            "mechanism_family",
            "affected_target",
            "direction",
            "interaction_partner",
        ],
        "reveal_policy": "Ground truth is scored only after explicit reveal. It is never fed back into the statistical investigator.",
    }


def score_revealed_diagnosis(
    records: list[dict[str, Any]],
    activation_unit: int,
    scenario_code: str,
    ground_truth: dict[str, Any],
) -> dict[str, Any]:
    """Score the frozen blind diagnosis against sealed simulator truth.

    Recomputing the investigator here is safe because its inputs remain only the
    observable records + activation boundary. The expected truth table is used
    solely to score the frozen prediction after reveal.
    """
    if scenario_code not in EXPECTED_ATTRIBUTION:
        raise ValueError(f"No arena scoring policy for scenario: {scenario_code}")
    inv = build_investigation_overview(records, activation_unit)
    top = inv["top_suspect"]
    attr = top.get("attribution") or {}
    expected = EXPECTED_ATTRIBUTION[scenario_code]

    checks = {
        "mechanism_family": top["code"] == expected["code"],
        "affected_target": _target_ok(str(top["target"]), expected),
        "direction": attr.get("direction") == expected["direction"],
        "interaction_partner": attr.get("interaction_partner") == expected["interaction"],
    }
    correct = sum(int(v) for v in checks.values())
    total = len(checks)
    score_pct = 100.0 * correct / total
    if correct == total:
        grade = "FULL_ATTRIBUTION_MATCH"
    elif checks["mechanism_family"] and checks["affected_target"]:
        grade = "MECHANISM_AND_TARGET_MATCH"
    elif checks["mechanism_family"]:
        grade = "MECHANISM_ONLY_MATCH"
    else:
        grade = "MISDIAGNOSIS"

    expected_target = expected.get("target") or f"{expected.get('target_prefix')}*"
    return {
        "grade": grade,
        "score": round(score_pct, 1),
        "dimensions_correct": correct,
        "dimensions_total": total,
        "checks": checks,
        "blind_prediction": {
            "code": top["code"],
            "target": top["target"],
            "direction": attr.get("direction"),
            "interaction_partner": attr.get("interaction_partner"),
            "evidence_score": top["evidence_score"],
            "status": top["status"],
        },
        "expected_attribution": {
            "code": expected["code"],
            "target": expected_target,
            "direction": expected["direction"],
            "interaction_partner": expected["interaction"],
        },
        "ground_truth": ground_truth,
        "causal_firewall": {
            "truth_used_by_blind_investigator": False,
            "truth_used_for_post_reveal_scoring_only": True,
        },
        "benchmark_note": "This score evaluates attribution inside the deterministic synthetic Hidden Factory. It is not a real-factory accuracy claim.",
    }
