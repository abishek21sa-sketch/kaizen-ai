from __future__ import annotations

import csv
import io
import math
from datetime import datetime
from typing import Any, Iterable

from .contract import COMMON_ALIASES, FULL_ENGINE_REQUIRED_FIELDS, STATION_TIME_FIELDS, assess_fields

BOOL_TRUE = {"1", "true", "t", "yes", "y", "fail", "failed", "defect"}
BOOL_FALSE = {"0", "false", "f", "no", "n", "pass", "passed", "ok", ""}

NUMERIC_FIELDS = {
    "fixture_age_cycles", "ambient_temp_c", "humidity_pct", "torque_target_nm",
    "torque_measured_nm", "alignment_measured_mm", "adhesive_strength_measured_mpa",
    *STATION_TIME_FIELDS, "queue_wait_s", "total_processing_s", "copq_usd",
}
BOOL_FIELDS = {"observed_defect", "rework", "scrap"}


def _clean_key(value: str) -> str:
    return str(value).strip().lower().replace(" ", "_").replace("-", "_")


def build_mapping(source_fields: Iterable[str], explicit_mapping: dict[str, str] | None = None) -> dict[str, str]:
    """Return source-field -> canonical-field mapping.

    explicit_mapping accepts either source->canonical or canonical->source; orientation is
    detected from canonical names. Ambiguous/unrecognized fields are intentionally ignored.
    """
    source_fields = list(source_fields)
    normalized_source = {_clean_key(x): x for x in source_fields}
    result: dict[str, str] = {}

    if explicit_mapping:
        for left, right in explicit_mapping.items():
            l, r = _clean_key(left), _clean_key(right)
            if r in FULL_ENGINE_REQUIRED_FIELDS or r in {"unit_index", "total_processing_s"}:
                src = normalized_source.get(l)
                if src:
                    result[src] = r
            elif l in FULL_ENGINE_REQUIRED_FIELDS or l in {"unit_index", "total_processing_s"}:
                src = normalized_source.get(r)
                if src:
                    result[src] = l

    canonical_candidates = set(FULL_ENGINE_REQUIRED_FIELDS) | {"unit_index", "total_processing_s"}
    for canonical in canonical_candidates:
        if canonical in result.values():
            continue
        if canonical in normalized_source:
            result[normalized_source[canonical]] = canonical
            continue
        for alias in COMMON_ALIASES.get(canonical, ()):
            key = _clean_key(alias)
            if key in normalized_source:
                result[normalized_source[key]] = canonical
                break
    return result


def _bool(value: Any, field: str) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    v = str(value).strip().lower()
    if v in BOOL_TRUE:
        return True
    if v in BOOL_FALSE:
        return False
    raise ValueError(f"{field} must be boolean-like; got {value!r}")


def _number(value: Any, field: str) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric; got {value!r}") from exc
    if not math.isfinite(out):
        raise ValueError(f"{field} must be finite")
    return out


def normalize_records(
    rows: list[dict[str, Any]],
    *,
    explicit_mapping: dict[str, str] | None = None,
    require_full_engine: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not rows:
        raise ValueError("At least one production record is required.")
    source_fields = list(rows[0].keys())
    mapping = build_mapping(source_fields, explicit_mapping)
    canonical_present = set(mapping.values())
    readiness = assess_fields(canonical_present)
    if require_full_engine and not readiness["full_engine_ready"]:
        raise ValueError(
            "Dataset cannot run the full KAIZEN engine. Missing canonical fields: "
            + ", ".join(readiness["missing_full_engine_fields"])
        )

    normalized: list[dict[str, Any]] = []
    for index, source in enumerate(rows):
        row: dict[str, Any] = {}
        for src, dst in mapping.items():
            if src in source:
                row[dst] = source[src]
        row["unit_index"] = int(row.get("unit_index", index))
        for field in NUMERIC_FIELDS:
            if field in row and row[field] not in (None, ""):
                row[field] = _number(row[field], field)
        if "fixture_age_cycles" in row:
            row["fixture_age_cycles"] = int(round(float(row["fixture_age_cycles"])))
        if "shift" in row:
            try:
                row["shift"] = int(row["shift"])
            except (TypeError, ValueError):
                row["shift"] = str(row["shift"])
        for field in BOOL_FIELDS:
            if field in row:
                row[field] = _bool(row[field], field)
        if "timestamp" in row:
            # Validate parseability but preserve original ISO-compatible text.
            text = str(row["timestamp"]).strip().replace("Z", "+00:00")
            try:
                datetime.fromisoformat(text)
            except ValueError as exc:
                raise ValueError(f"timestamp must be ISO-8601 compatible; got {row['timestamp']!r}") from exc
        if "total_processing_s" not in row and all(k in row for k in STATION_TIME_FIELDS) and "queue_wait_s" in row:
            row["total_processing_s"] = round(sum(float(row[k]) for k in STATION_TIME_FIELDS), 6)
        normalized.append(row)

    # Re-assess the normalized schema and preserve a transparent mapping report.
    canonical_fields = set().union(*(r.keys() for r in normalized))
    readiness = assess_fields(canonical_fields)
    return normalized, {
        "source_fields": source_fields,
        "mapping": mapping,
        "canonical_fields": sorted(canonical_fields),
        "readiness": readiness,
        "row_count": len(normalized),
        "fabricated_fields": [],
        "derived_fields": [x for x in ("unit_index", "total_processing_s") if x not in canonical_present],
    }


def parse_csv_bytes(data: bytes) -> list[dict[str, Any]]:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must be UTF-8 encoded.") from exc
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV has no header row.")
    return [dict(row) for row in reader]
