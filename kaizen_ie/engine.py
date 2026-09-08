from __future__ import annotations

from .capacity import line_balance, station_capacity
from .config import DEFAULT_IE_ASSUMPTIONS, IEAssumptions
from .flow import phase_flow_metrics
from .oee import calibration_oee
from .queueing import calibration_queue_metrics


def build_ie_overview(
    records: list[dict],
    activation_unit: int,
    *,
    assumptions: IEAssumptions = DEFAULT_IE_ASSUMPTIONS,
) -> dict:
    if not records:
        raise ValueError("records must not be empty")
    if not 1 <= activation_unit < len(records):
        raise ValueError("activation_unit must split the observable record set")

    pre = records[:activation_unit]
    post = records[activation_unit:]
    takt = assumptions.takt_seconds_per_unit
    required = assumptions.required_rate_units_per_hour

    pre_flow = phase_flow_metrics(pre, phase="pre")
    post_flow = phase_flow_metrics(post, phase="post")

    pre_cap = station_capacity(
        pre,
        phase="pre",
        required_rate_uph=required,
        observed_release_rate_uph=pre_flow["release_rate_units_per_hour"],
    )
    post_cap = station_capacity(
        post,
        phase="post",
        required_rate_uph=required,
        observed_release_rate_uph=post_flow["release_rate_units_per_hour"],
    )

    result = {
        "version": "ie-v0.3",
        "assumptions": assumptions.to_dict(),
        "takt": {
            "takt_seconds_per_unit": round(takt, 4),
            "required_rate_units_per_hour": round(required, 4),
            "pre_release_interval_s": pre_flow["median_release_interval_s"],
            "post_release_interval_s": post_flow["median_release_interval_s"],
            "pre_release_rate_units_per_hour": pre_flow["release_rate_units_per_hour"],
            "post_release_rate_units_per_hour": post_flow["release_rate_units_per_hour"],
            "release_policy_status": (
                "RELEASING_FASTER_THAN_CUSTOMER_TAKT"
                if min(pre_flow["median_release_interval_s"], post_flow["median_release_interval_s"]) < takt
                else "AT_OR_BELOW_CUSTOMER_TAKT"
            ),
        },
        "flow": {"pre": pre_flow, "post": post_flow},
        "capacity": {"pre": pre_cap, "post": post_cap},
        "line_balance": {
            "pre": line_balance(pre, phase="pre", takt_s=takt),
            "post": line_balance(post, phase="post", takt_s=takt),
        },
        "queueing": {
            "pre": calibration_queue_metrics(pre, phase="pre"),
            "post": calibration_queue_metrics(post, phase="post"),
        },
        "oee": {
            "pre": calibration_oee(pre, phase="pre"),
            "post": calibration_oee(post, phase="post"),
        },
        "demand_check": {
            "pre_throughput_meets_demand": pre_flow["throughput_units_per_hour"] >= required,
            "post_throughput_meets_demand": post_flow["throughput_units_per_hour"] >= required,
            "pre_good_throughput_meets_demand": pre_flow["good_throughput_units_per_hour"] >= required,
            "post_good_throughput_meets_demand": post_flow["good_throughput_units_per_hour"] >= required,
        },
        "evidence_state": {
            "ie_core": "IMPLEMENTED_AND_TESTED",
            "ground_truth_dependency": False,
            "causal_claims_allowed": False,
            "note": "V0.3 quantifies flow/capacity behavior from observable records only; it does not infer root cause.",
        },
    }
    return result
