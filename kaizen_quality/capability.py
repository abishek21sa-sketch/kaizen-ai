from __future__ import annotations

import math
import statistics
from typing import Any, Iterable

D2_N2 = 1.128


def _safe_std(values: list[float]) -> float:
    return statistics.stdev(values) if len(values) >= 2 else 0.0


def _within_sigma_imr(values: list[float]) -> tuple[float, float]:
    if len(values) < 2:
        return 0.0, 0.0
    mr = [abs(values[i] - values[i - 1]) for i in range(1, len(values))]
    mrbar = statistics.fmean(mr) if mr else 0.0
    sigma = mrbar / D2_N2 if mrbar > 0 else _safe_std(values)
    return sigma, mrbar


def capability_analysis(values: Iterable[float], *, lsl: float | None = None, usl: float | None = None) -> dict[str, Any]:
    vals = [float(v) for v in values]
    if len(vals) < 2:
        raise ValueError("capability requires at least two observations")
    if lsl is None and usl is None:
        raise ValueError("at least one specification limit is required")
    if lsl is not None and usl is not None and lsl >= usl:
        raise ValueError("lsl must be less than usl")

    mean = statistics.fmean(vals)
    sigma_overall = _safe_std(vals)
    sigma_within, mrbar = _within_sigma_imr(vals)

    def div(num: float, den: float) -> float | None:
        return num / den if den > 0 else None

    cp = div(usl - lsl, 6 * sigma_within) if lsl is not None and usl is not None else None
    cpu = div(usl - mean, 3 * sigma_within) if usl is not None else None
    cpl = div(mean - lsl, 3 * sigma_within) if lsl is not None else None
    cpk_candidates = [x for x in (cpu, cpl) if x is not None]
    cpk = min(cpk_candidates) if cpk_candidates else None

    pp = div(usl - lsl, 6 * sigma_overall) if lsl is not None and usl is not None else None
    ppu = div(usl - mean, 3 * sigma_overall) if usl is not None else None
    ppl = div(mean - lsl, 3 * sigma_overall) if lsl is not None else None
    ppk_candidates = [x for x in (ppu, ppl) if x is not None]
    ppk = min(ppk_candidates) if ppk_candidates else None

    index = cpk
    if index is None or math.isnan(index):
        status = "UNAVAILABLE"
    elif index >= 1.33:
        status = "CAPABLE"
    elif index >= 1.0:
        status = "MARGINAL"
    else:
        status = "NOT_CAPABLE"

    return {
        "n": len(vals), "mean": mean, "sigma_within": sigma_within, "sigma_overall": sigma_overall, "mrbar": mrbar,
        "lsl": lsl, "usl": usl, "cp": cp, "cpk": cpk, "cpu": cpu, "cpl": cpl,
        "pp": pp, "ppk": ppk, "ppu": ppu, "ppl": ppl, "status": status,
        "within_sigma_method": "Individuals moving-range estimator (MRbar / 1.128)",
    }


def _phase_rows(records: list[dict[str, Any]], activation_unit: int, phase: str) -> list[dict[str, Any]]:
    if phase == "pre":
        return [r for r in records if r["unit_index"] < activation_unit]
    if phase == "post":
        return [r for r in records if r["unit_index"] >= activation_unit]
    raise ValueError(phase)


def capability_suite(records: list[dict[str, Any]], activation_unit: int) -> dict[str, Any]:
    analyses: list[dict[str, Any]] = []
    for phase in ("pre", "post"):
        rows = _phase_rows(records, activation_unit, phase)
        # Torque is product-specific, so evaluate error from each unit's target on a common +/- 1.35 Nm specification.
        torque_error = [float(r["torque_measured_nm"]) - float(r["torque_target_nm"]) for r in rows]
        torque = capability_analysis(torque_error, lsl=-1.35, usl=1.35)
        torque.update({"metric": "Torque error", "unit": "Nm", "phase": phase, "scope": "All products normalized to target"})
        analyses.append(torque)

        alignment = capability_analysis([float(r["alignment_measured_mm"]) for r in rows], lsl=-0.20, usl=0.20)
        alignment.update({"metric": "Alignment", "unit": "mm", "phase": phase, "scope": "All products"})
        analyses.append(alignment)

        for product, lsl in (("A", 5.4), ("B", 5.7), ("C", 6.0)):
            vals = [float(r["adhesive_strength_measured_mpa"]) for r in rows if r["product_variant"] == product]
            if len(vals) >= 2:
                adh = capability_analysis(vals, lsl=lsl)
                adh.update({"metric": "Adhesive strength", "unit": "MPa", "phase": phase, "scope": f"Product {product}"})
                analyses.append(adh)

    return {"analyses": analyses, "note": "Cp/Cpk use the I-MR within-sigma estimator; Pp/Ppk use overall sample standard deviation."}
