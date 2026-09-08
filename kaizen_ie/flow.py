from __future__ import annotations

import math
import statistics
from datetime import datetime
from typing import Iterable


TRANSFORMATION_COLUMNS = (
    "bearing_press_s",
    "motor_assembly_s",
    "adhesive_dispense_s",
    "torque_fastening_s",
)
NECESSARY_NVA_COLUMNS = (
    "calibration_s",
    "functional_test_s",
    "final_inspection_s",
)


def _seconds(ts: str, origin: datetime) -> float:
    return (datetime.fromisoformat(ts) - origin).total_seconds()


def _time_weighted_count(intervals: Iterable[tuple[float, float]]) -> tuple[float, int, float]:
    """Return time-weighted average count, max count, and horizon seconds.

    Intervals are treated as half-open [start, end). The calculation starts empty and ends
    empty, which makes it a useful exact Little's-Law reference for the supplied cohort.
    """
    intervals = [(float(a), float(b)) for a, b in intervals if b >= a]
    if not intervals:
        return 0.0, 0, 0.0
    events: list[tuple[float, int]] = []
    for start, end in intervals:
        events.append((start, +1))
        events.append((end, -1))
    # departures before arrivals at identical timestamps avoids a false instantaneous spike
    events.sort(key=lambda x: (x[0], x[1]))
    first = events[0][0]
    last = events[-1][0]
    if last <= first:
        return 0.0, 0, 0.0
    current = 0
    max_count = 0
    area = 0.0
    prev = first
    for t, delta in events:
        area += current * (t - prev)
        current += delta
        max_count = max(max_count, current)
        prev = t
    return area / (last - first), max_count, last - first


def _safe_pct_error(actual: float, expected: float) -> float:
    if abs(expected) < 1e-12:
        return 0.0 if abs(actual) < 1e-12 else math.inf
    return abs(actual - expected) / abs(expected) * 100.0


def phase_flow_metrics(rows: list[dict], *, phase: str) -> dict:
    if not rows:
        return {"phase": phase, "n": 0}
    origin = datetime.fromisoformat(rows[0]["timestamp"])
    launches: list[float] = []
    completions: list[float] = []
    line_intervals: list[tuple[float, float]] = []
    flow_times: list[float] = []
    waits: list[float] = []
    va_times: list[float] = []
    necessary_times: list[float] = []
    good = 0
    for r in rows:
        launch = _seconds(r["timestamp"], origin)
        wait = float(r["queue_wait_s"])
        process = float(r["total_processing_s"])
        completion = launch + process + wait
        flow = process + wait
        launches.append(launch)
        completions.append(completion)
        line_intervals.append((launch, completion))
        flow_times.append(flow)
        waits.append(wait)
        va_times.append(sum(float(r[c]) for c in TRANSFORMATION_COLUMNS))
        necessary_times.append(sum(float(r[c]) for c in NECESSARY_NVA_COLUMNS))
        good += int(not r["observed_defect"])

    avg_wip, max_wip, horizon_s = _time_weighted_count(line_intervals)
    throughput_uph = len(rows) / horizon_s * 3600.0 if horizon_s > 0 else 0.0
    good_throughput_uph = good / horizon_s * 3600.0 if horizon_s > 0 else 0.0
    avg_flow_s = statistics.fmean(flow_times)
    little_expected = (throughput_uph / 3600.0) * avg_flow_s
    avg_va = statistics.fmean(va_times)
    avg_necessary = statistics.fmean(necessary_times)
    avg_wait = statistics.fmean(waits)
    avg_lead = avg_va + avg_necessary + avg_wait
    pce = avg_va / avg_lead if avg_lead > 0 else 0.0

    launch_diffs = [b - a for a, b in zip(launches, launches[1:]) if b > a]
    median_release_interval = statistics.median(launch_diffs) if launch_diffs else 0.0
    release_rate = 3600.0 / median_release_interval if median_release_interval > 0 else 0.0

    return {
        "phase": phase,
        "n": len(rows),
        "horizon_s": round(horizon_s, 4),
        "throughput_units_per_hour": round(throughput_uph, 4),
        "good_throughput_units_per_hour": round(good_throughput_uph, 4),
        "first_pass_yield": round(good / len(rows), 6),
        "mean_flow_time_s": round(avg_flow_s, 4),
        "median_flow_time_s": round(statistics.median(flow_times), 4),
        "mean_queue_wait_s": round(avg_wait, 4),
        "p95_queue_wait_s": round(_percentile(waits, 0.95), 4),
        "average_wip_units": round(avg_wip, 6),
        "max_wip_units": max_wip,
        "little_law_expected_wip": round(little_expected, 6),
        "little_law_error_pct": round(_safe_pct_error(avg_wip, little_expected), 9),
        "median_release_interval_s": round(median_release_interval, 4),
        "release_rate_units_per_hour": round(release_rate, 4),
        "value_stream": {
            "mean_value_added_s": round(avg_va, 4),
            "mean_necessary_nva_s": round(avg_necessary, 4),
            "mean_wait_s": round(avg_wait, 4),
            "mean_lead_time_s": round(avg_lead, 4),
            "process_cycle_efficiency": round(pce, 6),
            "classification_note": (
                "Bearing press, motor assembly, adhesive dispense and torque fastening are treated as transformation time. "
                "Calibration/test/inspection are treated as necessary non-value-added time; calibration queue is pure waiting."
            ),
        },
    }


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return xs[lo]
    frac = pos - lo
    return xs[lo] * (1 - frac) + xs[hi] * frac


__all__ = ["phase_flow_metrics", "_time_weighted_count", "_percentile"]
