from __future__ import annotations

from collections import Counter
from typing import Any

REQUIRED_FIELDS = {
    "unit_index", "unit_id", "timestamp", "product_variant", "operator_id", "machine_id", "fixture_id", "gage_id",
    "supplier_lot", "torque_target_nm", "torque_measured_nm", "alignment_measured_mm",
    "adhesive_strength_measured_mpa", "queue_wait_s", "observed_defect", "defect_type", "rework", "scrap", "copq_usd",
}


def data_quality_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {"status": "FAIL", "score": 0, "checks": [], "row_count": 0}

    keys = set(records[0])
    missing_fields = sorted(REQUIRED_FIELDS - keys)
    unit_ids = [str(r.get("unit_id", "")) for r in records]
    duplicates = sum(c - 1 for c in Counter(unit_ids).values() if c > 1)
    missing_cells = sum(1 for r in records for f in REQUIRED_FIELDS if r.get(f) is None or r.get(f) == "")
    negative_waits = sum(float(r["queue_wait_s"]) < 0 for r in records)
    inconsistent_disposition = sum(bool(r["rework"]) and bool(r["scrap"]) for r in records)
    bad_defect_flags = sum((not bool(r["observed_defect"])) and str(r["defect_type"]) != "NONE" for r in records)

    checks = [
        {"name": "Required observable fields", "passed": not missing_fields, "detail": missing_fields or "All required fields present"},
        {"name": "Unique unit identifiers", "passed": duplicates == 0, "detail": f"{duplicates} duplicate rows"},
        {"name": "Required-field completeness", "passed": missing_cells == 0, "detail": f"{missing_cells} missing cells"},
        {"name": "Non-negative queue wait", "passed": negative_waits == 0, "detail": f"{negative_waits} invalid queue values"},
        {"name": "Disposition consistency", "passed": inconsistent_disposition == 0, "detail": f"{inconsistent_disposition} units marked rework and scrap"},
        {"name": "Defect-label consistency", "passed": bad_defect_flags == 0, "detail": f"{bad_defect_flags} inconsistent defect labels"},
    ]
    passed = sum(c["passed"] for c in checks)
    score = round(100 * passed / len(checks), 1)
    return {"status": "PASS" if passed == len(checks) else "WARN", "score": score, "checks": checks, "row_count": len(records)}
