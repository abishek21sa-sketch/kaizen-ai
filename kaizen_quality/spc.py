from __future__ import annotations

import math
import statistics
from typing import Any

D2_N2 = 1.128
D4_N2 = 3.267


def _signals(values: list[float], center: float, ucl: float, lcl: float) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    n = len(values)
    for i, v in enumerate(values):
        if v > ucl or v < lcl:
            signals.append({"index": i, "rule": "POINT_BEYOND_3SIGMA", "value": v})

    # Eight consecutive observations on one side of center.
    for start in range(0, n - 7):
        block = values[start:start + 8]
        if all(v > center for v in block) or all(v < center for v in block):
            signals.append({"index": start + 7, "rule": "EIGHT_ON_ONE_SIDE", "value": values[start + 7]})

    # Six consecutive strictly increasing/decreasing observations.
    for start in range(0, n - 5):
        block = values[start:start + 6]
        if all(block[j] < block[j + 1] for j in range(5)) or all(block[j] > block[j + 1] for j in range(5)):
            signals.append({"index": start + 5, "rule": "SIX_POINT_TREND", "value": values[start + 5]})

    # De-duplicate same rule/index.
    unique = {(s["index"], s["rule"]): s for s in signals}
    return list(unique.values())


def individuals_mr_chart(values: list[float], baseline_n: int) -> dict[str, Any]:
    if baseline_n < 2 or baseline_n > len(values):
        raise ValueError("baseline_n must include at least two and no more than all observations")
    baseline = values[:baseline_n]
    center = statistics.fmean(baseline)
    moving_ranges = [abs(baseline[i] - baseline[i - 1]) for i in range(1, len(baseline))]
    mrbar = statistics.fmean(moving_ranges)
    sigma = mrbar / D2_N2 if mrbar > 0 else statistics.stdev(baseline)
    ucl = center + 3 * sigma
    lcl = center - 3 * sigma
    mr_ucl = D4_N2 * mrbar
    signals = _signals(values, center, ucl, lcl)
    return {
        "center": center, "ucl": ucl, "lcl": lcl, "sigma_within": sigma, "mrbar": mrbar,
        "mr_ucl": mr_ucl, "mr_lcl": 0.0, "signals": signals,
    }


def p_chart(defect_flags: list[bool], subgroup_size: int, baseline_n: int) -> dict[str, Any]:
    if subgroup_size < 2:
        raise ValueError("subgroup_size must be at least 2")
    groups = []
    for start in range(0, len(defect_flags), subgroup_size):
        block = defect_flags[start:start + subgroup_size]
        if not block:
            continue
        groups.append({"start_index": start, "n": len(block), "defects": sum(bool(x) for x in block), "p": sum(bool(x) for x in block) / len(block)})

    baseline_groups = [g for g in groups if g["start_index"] < baseline_n]
    base_n = sum(g["n"] for g in baseline_groups)
    base_defects = sum(g["defects"] for g in baseline_groups)
    pbar = base_defects / max(1, base_n)
    for g in groups:
        sigma = math.sqrt(max(0.0, pbar * (1 - pbar) / g["n"]))
        g["ucl"] = min(1.0, pbar + 3 * sigma)
        g["lcl"] = max(0.0, pbar - 3 * sigma)
        g["signal"] = g["p"] > g["ucl"] or g["p"] < g["lcl"]
    return {"center": pbar, "subgroup_size": subgroup_size, "groups": groups, "signal_count": sum(g["signal"] for g in groups)}


def spc_suite(records: list[dict[str, Any]], activation_unit: int, max_points: int = 350) -> dict[str, Any]:
    torque_error = [float(r["torque_measured_nm"]) - float(r["torque_target_nm"]) for r in records]
    imr = individuals_mr_chart(torque_error, activation_unit)
    for s in imr["signals"]:
        s["unit_index"] = int(records[s["index"]]["unit_index"])
        s["unit_id"] = records[s["index"]]["unit_id"]
    step = max(1, math.ceil(len(records) / max_points))
    series = [
        {"unit_index": int(records[i]["unit_index"]), "value": torque_error[i], "incident_active": i >= activation_unit}
        for i in range(0, len(records), step)
    ]
    p = p_chart([bool(r["observed_defect"]) for r in records], subgroup_size=50, baseline_n=activation_unit)
    return {
        "torque_error_imr": {**imr, "series": series, "series_step": step, "signal_count": len(imr["signals"])},
        "defect_p_chart": p,
        "baseline_policy": "Control limits are estimated from pre-incident observable data and held fixed for post-incident monitoring.",
    }
