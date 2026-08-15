from __future__ import annotations

import statistics

from kaizen_factory.simulator import PRODUCTS


def calibration_oee(rows: list[dict], *, phase: str) -> dict:
    """Observable calibration-cell OEE diagnostic.

    V0.3's observable schema has no separate downtime-state event stream. Availability is
    therefore explicitly held at 100% rather than inferred from utilization. Performance
    captures speed/microstop/changeover losses through ideal-vs-observed calibration time.
    Quality uses observed first-pass yield. This limitation is surfaced in the result.
    """
    if not rows:
        return {"phase": phase, "n": 0}
    ideal = sum(float(PRODUCTS[r["product_variant"]]["calibration_s"]) for r in rows)
    actual = sum(float(r["calibration_s"]) for r in rows)
    performance = min(1.0, ideal / actual) if actual > 0 else 0.0
    quality = sum(int(not r["observed_defect"]) for r in rows) / len(rows)
    availability = 1.0
    oee = availability * performance * quality
    return {
        "phase": phase,
        "scope": "Calibration cell observable OEE diagnostic",
        "n": len(rows),
        "availability": round(availability, 6),
        "performance": round(performance, 6),
        "quality": round(quality, 6),
        "oee": round(oee, 6),
        "ideal_calibration_work_s": round(ideal, 4),
        "observed_calibration_busy_s": round(actual, 4),
        "availability_status": "ASSUMED_100_PERCENT",
        "availability_note": (
            "The V0.3 observable schema does not contain a separate planned-vs-unplanned downtime-state stream. "
            "Availability is intentionally not fabricated from utilization; it is held at 100% and flagged."
        ),
        "performance_note": "Ideal product-specific calibration time divided by observed calibration busy time, capped at 100%.",
        "quality_note": "Observed first-pass good units divided by total units in the phase.",
    }
