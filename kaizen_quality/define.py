from __future__ import annotations

from typing import Any


def build_define_package(records: list[dict[str, Any]], activation_unit: int, line_name: str) -> dict[str, Any]:
    pre = [r for r in records if r["unit_index"] < activation_unit]
    post = [r for r in records if r["unit_index"] >= activation_unit]

    def rate(rows: list[dict[str, Any]]) -> float:
        return sum(bool(r["observed_defect"]) for r in rows) / max(1, len(rows))

    def mean(rows: list[dict[str, Any]], key: str) -> float:
        return sum(float(r[key]) for r in rows) / max(1, len(rows))

    pre_def, post_def = rate(pre), rate(post)
    pre_wait, post_wait = mean(pre, "queue_wait_s"), mean(post, "queue_wait_s")
    defect_delta_pp = (post_def - pre_def) * 100
    wait_delta = post_wait - pre_wait

    if abs(defect_delta_pp) >= 1.0:
        problem = (
            f"Observed defect rate changed from {pre_def:.2%} before the incident to {post_def:.2%} after activation "
            f"({defect_delta_pp:+.2f} percentage points) on {line_name}."
        )
        goal = "Restore observed defect performance to the pre-incident baseline or better while preserving throughput and measurement integrity."
        primary_y = "Observed defect rate"
    else:
        problem = (
            f"Average calibration queue wait changed from {pre_wait:.1f} s before the incident to {post_wait:.1f} s after activation "
            f"({wait_delta:+.1f} s) on {line_name}."
        )
        goal = "Restore queue/flow performance to the pre-incident baseline or better without creating a quality tradeoff."
        primary_y = "Calibration queue wait"

    return {
        "project_charter": {
            "title": "Blind Incident DMAIC Investigation",
            "line": line_name,
            "problem_statement": problem,
            "business_case": (
                "Quality losses create rework/scrap COPQ while flow losses consume capacity and extend lead time. "
                "The project will separate process, material, measurement, and flow explanations before recommending action."
            ),
            "goal_statement": goal,
            "primary_y": primary_y,
            "scope_in": ["Actuator Assembly Line A", "observable production records", "torque/alignment/adhesive CTQs", "calibration queue"],
            "scope_out": ["sealed simulator ground truth", "unobserved plant systems", "unsupported financial extrapolation"],
        },
        "voc_ctq": [
            {"voice": "Fasteners must meet torque requirements.", "ctq": "Torque error from product target", "spec": "Target ± 1.35 Nm"},
            {"voice": "Assembly alignment must remain stable.", "ctq": "Alignment", "spec": "-0.20 to +0.20 mm"},
            {"voice": "Bond strength must exceed product requirement.", "ctq": "Adhesive strength", "spec": "A ≥ 5.4, B ≥ 5.7, C ≥ 6.0 MPa"},
            {"voice": "Production should flow without excessive waiting.", "ctq": "Calibration queue wait", "spec": "Operational baseline / improvement metric"},
        ],
        "sipoc": {
            "suppliers": ["Material suppliers S1/S2/S3", "maintenance", "operators", "measurement system"],
            "inputs": ["components", "adhesive lot", "fixture/tool condition", "product variant", "environment", "gage"],
            "process": ["bearing press", "motor assembly", "adhesive dispense", "torque fastening", "calibration", "functional test", "final inspection"],
            "outputs": ["assembled actuator", "CTQ measurements", "defect/rework/scrap disposition", "flow-time record"],
            "customers": ["downstream assembly", "quality engineering", "operations", "end customer"],
        },
    }
