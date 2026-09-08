from __future__ import annotations

import math
import statistics

from .flow import _percentile

STATIONS = (
    ("Bearing Press", "bearing_press_s"),
    ("Motor Assembly", "motor_assembly_s"),
    ("Adhesive Dispense", "adhesive_dispense_s"),
    ("Torque Fastening", "torque_fastening_s"),
    ("Calibration", "calibration_s"),
    ("Functional Test", "functional_test_s"),
    ("Final Inspection", "final_inspection_s"),
)


def station_capacity(rows: list[dict], *, phase: str, required_rate_uph: float, observed_release_rate_uph: float) -> dict:
    stations: list[dict] = []
    if not rows:
        return {"phase": phase, "stations": [], "bottleneck": None}
    for name, col in STATIONS:
        values = [float(r[col]) for r in rows]
        mean_s = statistics.fmean(values)
        capacity = 3600.0 / mean_s if mean_s > 0 else 0.0
        demand_load = required_rate_uph / capacity if capacity > 0 else float("inf")
        release_load = observed_release_rate_uph / capacity if capacity > 0 else float("inf")
        status = "CAPACITY_CONSTRAINED" if demand_load > 1.0 else "AT_RISK" if demand_load >= 0.90 else "AVAILABLE"
        stations.append(
            {
                "station": name,
                "column": col,
                "phase": phase,
                "mean_service_s": round(mean_s, 4),
                "p95_service_s": round(_percentile(values, 0.95), 4),
                "capacity_units_per_hour": round(capacity, 4),
                "demand_utilization": round(demand_load, 6),
                "release_utilization": round(release_load, 6),
                "status": status,
            }
        )
    bottleneck = min(stations, key=lambda x: x["capacity_units_per_hour"])
    return {"phase": phase, "stations": stations, "bottleneck": bottleneck}


def line_balance(rows: list[dict], *, phase: str, takt_s: float) -> dict:
    if not rows:
        return {"phase": phase, "n": 0}
    means = []
    for name, col in STATIONS:
        vals = [float(r[col]) for r in rows]
        means.append((name, statistics.fmean(vals)))
    total = sum(v for _, v in means)
    intrinsic_cycle = max(v for _, v in means)
    n = len(means)
    intrinsic_eff = total / (n * intrinsic_cycle) if intrinsic_cycle > 0 else 0.0
    takt_eff = total / (n * takt_s) if takt_s > 0 else 0.0
    smoothness = math.sqrt(sum((intrinsic_cycle - v) ** 2 for _, v in means))
    exceeding = [name for name, v in means if v > takt_s]
    return {
        "phase": phase,
        "station_count": n,
        "total_work_content_s": round(total, 4),
        "intrinsic_cycle_time_s": round(intrinsic_cycle, 4),
        "intrinsic_balance_efficiency": round(intrinsic_eff, 6),
        "intrinsic_balance_delay": round(1.0 - intrinsic_eff, 6),
        "balance_efficiency_at_takt": round(takt_eff, 6),
        "smoothness_index_s": round(smoothness, 4),
        "stations_exceeding_takt": exceeding,
        "takt_feasible_with_one_resource_each": len(exceeding) == 0,
        "station_mean_work_s": [{"station": name, "mean_s": round(v, 4)} for name, v in means],
    }
