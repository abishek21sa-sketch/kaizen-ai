from __future__ import annotations

import statistics
from datetime import datetime

from .flow import _time_weighted_count


def calibration_queue_metrics(rows: list[dict], *, phase: str) -> dict:
    """Empirical calibration-cell queue metrics reconstructed from observable records.

    This does not assume M/M/1. It reconstructs arrival/start/departure intervals from the
    recorded launch timestamp, upstream processing times, queue wait, and calibration time.
    """
    if not rows:
        return {"phase": phase, "n": 0}
    origin = datetime.fromisoformat(rows[0]["timestamp"])
    arrivals: list[float] = []
    starts: list[float] = []
    departures: list[float] = []
    waits: list[float] = []
    service: list[float] = []
    queue_intervals: list[tuple[float, float]] = []
    cell_intervals: list[tuple[float, float]] = []

    for r in rows:
        launch = (datetime.fromisoformat(r["timestamp"]) - origin).total_seconds()
        upstream = sum(float(r[c]) for c in ("bearing_press_s", "motor_assembly_s", "adhesive_dispense_s", "torque_fastening_s"))
        arrival = launch + upstream
        wait = float(r["queue_wait_s"])
        start = arrival + wait
        svc = float(r["calibration_s"])
        departure = start + svc
        arrivals.append(arrival)
        starts.append(start)
        departures.append(departure)
        waits.append(wait)
        service.append(svc)
        queue_intervals.append((arrival, start))
        cell_intervals.append((arrival, departure))

    avg_lq, max_lq, queue_horizon = _time_weighted_count(queue_intervals)
    avg_l, max_l, cell_horizon = _time_weighted_count(cell_intervals)
    cell_horizon = max(cell_horizon, 1e-12)
    queue_horizon = max(queue_horizon, 1e-12)
    lam_cell_s = len(rows) / cell_horizon
    lam_queue_s = len(rows) / queue_horizon
    avg_wq = statistics.fmean(waits)
    avg_s = statistics.fmean(service)
    avg_w = avg_wq + avg_s
    little_lq = lam_queue_s * avg_wq
    little_l = lam_cell_s * avg_w
    service_rate_uph = 3600.0 / avg_s if avg_s > 0 else 0.0
    arrival_rate_uph = lam_cell_s * 3600.0

    return {
        "phase": phase,
        "n": len(rows),
        "arrival_rate_units_per_hour": round(arrival_rate_uph, 4),
        "service_rate_units_per_hour": round(service_rate_uph, 4),
        "traffic_intensity_lambda_over_mu": round(arrival_rate_uph / service_rate_uph, 6) if service_rate_uph else None,
        "mean_service_s": round(avg_s, 4),
        "mean_wait_s": round(avg_wq, 4),
        "mean_time_in_cell_s": round(avg_w, 4),
        "probability_waited": round(sum(w > 1e-9 for w in waits) / len(waits), 6),
        "average_queue_wip_units": round(avg_lq, 6),
        "max_queue_wip_units": max_lq,
        "average_cell_wip_units": round(avg_l, 6),
        "max_cell_wip_units": max_l,
        "little_law_queue_expected_lq": round(little_lq, 6),
        "little_law_cell_expected_l": round(little_l, 6),
        "little_law_queue_error_pct": round(_pct_error(avg_lq, little_lq), 9),
        "little_law_cell_error_pct": round(_pct_error(avg_l, little_l), 9),
        "method": "Empirical event reconstruction; no M/M/1 distributional assumption.",
    }


def _pct_error(actual: float, expected: float) -> float:
    if abs(expected) < 1e-12:
        return 0.0 if abs(actual) < 1e-12 else float("inf")
    return abs(actual - expected) / abs(expected) * 100.0
