from __future__ import annotations

import math
import random
import statistics
from collections import defaultdict
from typing import Any


def crossed_gage_rr(readings: list[dict[str, Any]]) -> dict[str, Any]:
    if not readings:
        raise ValueError("readings are required")
    parts = sorted({str(r["part"]) for r in readings})
    appraisers = sorted({str(r["appraiser"]) for r in readings})
    cell: defaultdict[tuple[str, str], list[float]] = defaultdict(list)
    for r in readings:
        cell[(str(r["part"]), str(r["appraiser"]))].append(float(r["value"]))
    repeats = {len(v) for v in cell.values()}
    if len(repeats) != 1 or not repeats or min(repeats) < 2:
        raise ValueError("balanced crossed study requires at least two repeats per part/appraiser cell")
    if len(cell) != len(parts) * len(appraisers):
        raise ValueError("balanced crossed study requires every part/appraiser combination")
    nr = repeats.pop()
    nparts, nops = len(parts), len(appraisers)
    if nparts < 2 or nops < 2:
        raise ValueError("crossed study requires at least two parts and two appraisers")

    vals = [float(r["value"]) for r in readings]
    grand = statistics.fmean(vals)
    part_mean = {p: statistics.fmean([float(r["value"]) for r in readings if str(r["part"]) == p]) for p in parts}
    op_mean = {o: statistics.fmean([float(r["value"]) for r in readings if str(r["appraiser"]) == o]) for o in appraisers}
    cell_mean = {(p, o): statistics.fmean(cell[(p, o)]) for p in parts for o in appraisers}

    ss_part = nops * nr * sum((part_mean[p] - grand) ** 2 for p in parts)
    ss_op = nparts * nr * sum((op_mean[o] - grand) ** 2 for o in appraisers)
    ss_inter = nr * sum((cell_mean[(p, o)] - part_mean[p] - op_mean[o] + grand) ** 2 for p in parts for o in appraisers)
    ss_repeat = sum((float(r["value"]) - cell_mean[(str(r["part"]), str(r["appraiser"]))]) ** 2 for r in readings)

    df_part = nparts - 1
    df_op = nops - 1
    df_inter = (nparts - 1) * (nops - 1)
    df_repeat = nparts * nops * (nr - 1)
    ms_part = ss_part / df_part
    ms_op = ss_op / df_op
    ms_inter = ss_inter / df_inter
    ms_repeat = ss_repeat / df_repeat

    var_repeat = max(ms_repeat, 0.0)
    var_inter = max((ms_inter - ms_repeat) / nr, 0.0)
    var_op = max((ms_op - ms_inter) / (nparts * nr), 0.0)
    var_part = max((ms_part - ms_inter) / (nops * nr), 0.0)
    var_grr = var_repeat + var_op + var_inter
    var_total = var_grr + var_part
    sd_repeat = math.sqrt(var_repeat)
    sd_repro = math.sqrt(var_op + var_inter)
    sd_grr = math.sqrt(var_grr)
    sd_part = math.sqrt(var_part)
    sd_total = math.sqrt(var_total)
    pct_study = 100 * sd_grr / sd_total if sd_total > 0 else 0.0
    ndc = int(math.floor(1.41 * sd_part / sd_grr)) if sd_grr > 0 else 99

    if pct_study < 10:
        status = "ACCEPTABLE"
    elif pct_study <= 30:
        status = "CONDITIONAL"
    else:
        status = "UNACCEPTABLE"

    return {
        "design": {"parts": nparts, "appraisers": nops, "repeats": nr, "readings": len(readings)},
        "variance_components": {
            "repeatability": var_repeat, "appraiser": var_op, "part_appraiser_interaction": var_inter,
            "part_to_part": var_part, "gage_rr": var_grr, "total": var_total,
        },
        "study_sd": {"repeatability": sd_repeat, "reproducibility": sd_repro, "gage_rr": sd_grr, "part_to_part": sd_part, "total": sd_total},
        "pct_study_variation_grr": pct_study, "ndc": ndc, "status": status,
        "method": "Balanced crossed random-effects ANOVA variance components",
    }


def generate_baseline_msa_study(records: list[dict[str, Any]], activation_unit: int, seed: int) -> dict[str, Any]:
    pre = [r for r in records if r["unit_index"] < activation_unit]
    if len(pre) < 30:
        raise ValueError("not enough baseline units for MSA demonstration")
    rng = random.Random(seed ^ 0x5A17)
    # Select 10 spread-out baseline parts so the study contains real part-to-part variation from observable data.
    indices = [round(i * (len(pre) - 1) / 9) for i in range(10)]
    parts = [pre[i] for i in indices]
    appraisers = {"A": 0.00, "B": 0.025, "C": -0.018}
    readings: list[dict[str, Any]] = []
    for pidx, part in enumerate(parts, start=1):
        reference = float(part["torque_measured_nm"])
        for appraiser, bias in appraisers.items():
            for repeat in (1, 2):
                value = reference + bias + rng.gauss(0, 0.055)
                readings.append({"part": f"P{pidx:02d}", "appraiser": appraiser, "repeat": repeat, "value": value})
    result = crossed_gage_rr(readings)
    result["study_note"] = (
        "Designed crossed Gage R&R demonstration using 10 observable pre-incident parts, three appraisers, and two repeats. "
        "The study is generated independently of sealed ground truth."
    )
    result["readings_preview"] = readings[:12]
    return result


def gage_stratification(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in records:
        groups[str(r["gage_id"])].append(r)
    out = []
    for gage, rows in sorted(groups.items()):
        residuals = [float(r["torque_measured_nm"]) - float(r["torque_target_nm"]) for r in rows]
        out.append({
            "gage_id": gage, "n": len(rows), "mean_torque_error_nm": statistics.fmean(residuals),
            "sd_torque_error_nm": statistics.stdev(residuals) if len(residuals) >= 2 else 0.0,
            "observed_defect_rate": sum(bool(r["observed_defect"]) for r in rows) / max(1, len(rows)),
        })
    return out
