from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

CONTRACT_VERSION = "1.0"

STATION_TIME_FIELDS = (
    "bearing_press_s",
    "motor_assembly_s",
    "adhesive_dispense_s",
    "torque_fastening_s",
    "calibration_s",
    "functional_test_s",
    "final_inspection_s",
)

# These fields are the observable signals consumed by the current full KAIZEN stack.
# unit_index and total_processing_s can be derived by the adapter and therefore are
# intentionally not required at the source boundary.
FULL_ENGINE_REQUIRED_FIELDS = (
    "unit_id",
    "timestamp",
    "shift",
    "product_variant",
    "operator_id",
    "machine_id",
    "fixture_id",
    "fixture_age_cycles",
    "gage_id",
    "supplier",
    "supplier_lot",
    "ambient_temp_c",
    "humidity_pct",
    "torque_target_nm",
    "torque_measured_nm",
    "alignment_measured_mm",
    "adhesive_strength_measured_mpa",
    *STATION_TIME_FIELDS,
    "queue_wait_s",
    "observed_defect",
    "defect_type",
    "rework",
    "scrap",
    "copq_usd",
)

CANONICAL_FIELDS = ("unit_index", *FULL_ENGINE_REQUIRED_FIELDS, "total_processing_s")

# Common aliases are deliberately conservative. A production deployment should store
# plant-specific mappings rather than silently guessing ambiguous names.
COMMON_ALIASES: dict[str, tuple[str, ...]] = {
    "unit_id": ("unit", "serial", "serial_number", "part_id", "work_order_unit"),
    "timestamp": ("event_time", "time", "datetime", "completed_at"),
    "shift": ("shift_id", "crew_shift"),
    "product_variant": ("product", "sku", "variant", "part_number"),
    "operator_id": ("operator", "employee_id"),
    "machine_id": ("machine", "equipment_id", "asset_id"),
    "fixture_id": ("fixture", "tooling_id"),
    "fixture_age_cycles": ("fixture_cycles", "tooling_age_cycles"),
    "gage_id": ("gage", "gauge_id", "inspection_gage"),
    "supplier": ("supplier_id", "vendor"),
    "supplier_lot": ("lot", "material_lot", "supplier_lot_id"),
    "ambient_temp_c": ("temperature_c", "ambient_temperature_c"),
    "humidity_pct": ("humidity", "relative_humidity_pct"),
    "torque_target_nm": ("target_torque_nm", "torque_target"),
    "torque_measured_nm": ("torque_nm", "measured_torque_nm", "torque_measured"),
    "alignment_measured_mm": ("alignment_mm", "measured_alignment_mm"),
    "adhesive_strength_measured_mpa": ("adhesive_strength_mpa", "bond_strength_mpa"),
    "bearing_press_s": ("bearing_press_sec",),
    "motor_assembly_s": ("motor_assembly_sec",),
    "adhesive_dispense_s": ("adhesive_dispense_sec",),
    "torque_fastening_s": ("torque_fastening_sec",),
    "calibration_s": ("calibration_sec",),
    "functional_test_s": ("functional_test_sec",),
    "final_inspection_s": ("final_inspection_sec",),
    "queue_wait_s": ("queue_seconds", "wait_s", "queue_wait_sec"),
    "observed_defect": ("defect", "is_defect", "failed"),
    "defect_type": ("failure_mode", "defect_code"),
    "rework": ("is_rework",),
    "scrap": ("is_scrap",),
    "copq_usd": ("copq", "quality_cost_usd"),
}

@dataclass(frozen=True)
class Capability:
    code: str
    label: str
    fields: tuple[str, ...]


CAPABILITIES = (
    Capability("quality", "Lean Six Sigma / quality", (
        "torque_target_nm", "torque_measured_nm", "alignment_measured_mm",
        "adhesive_strength_measured_mpa", "gage_id", "observed_defect", "defect_type",
        "rework", "scrap", "copq_usd",
    )),
    Capability("flow", "Flow / Little's Law", ("timestamp", *STATION_TIME_FIELDS, "queue_wait_s")),
    Capability("capacity", "Capacity / bottleneck / line balance", STATION_TIME_FIELDS),
    Capability("oee_quality", "OEE quality/performance", (*STATION_TIME_FIELDS, "observed_defect", "product_variant")),
    Capability("investigator", "Statistical investigator", (
        "machine_id", "gage_id", "fixture_id", "supplier", "supplier_lot", "operator_id",
        "shift", "product_variant", "ambient_temp_c", "humidity_pct", "torque_target_nm",
        "torque_measured_nm", "alignment_measured_mm", "adhesive_strength_measured_mpa",
        "calibration_s", "queue_wait_s", "observed_defect",
    )),
    Capability("decision", "Simulation / optimization", FULL_ENGINE_REQUIRED_FIELDS),
)


def contract_document() -> dict[str, Any]:
    return {
        "contract": "KAIZEN Manufacturing Data Contract",
        "version": CONTRACT_VERSION,
        "principle": "Source systems are mapped into a canonical observable-event schema. KAIZEN never fabricates unavailable plant signals; analytics are enabled only when their required fields are present.",
        "canonical_fields": list(CANONICAL_FIELDS),
        "full_engine_required_fields": list(FULL_ENGINE_REQUIRED_FIELDS),
        "derived_fields": {
            "unit_index": "assigned deterministically from row order when absent",
            "total_processing_s": "sum of the seven station service-time fields when absent",
        },
        "common_aliases": {k: list(v) for k, v in COMMON_ALIASES.items()},
        "capabilities": [asdict(x) | {"fields": list(x.fields)} for x in CAPABILITIES],
        "source_modes": {
            "DEMO": "Hidden Factory deterministic synthetic incidents with sealed causal truth.",
            "FILE": "Historical CSV/JSON production records mapped into the contract.",
            "REPLAY": "Historical canonical records emitted in event order for near-live demonstrations.",
            "LIVE": "Events appended to an explicit live session then finalized into an analysis run.",
        },
        "real_world_causal_policy": "External FILE/REPLAY/LIVE runs have no synthetic ground truth and cannot use KAIZEN's synthetic DOE executor or truth-reveal scorecard. A real intervention must be performed outside KAIZEN and its results ingested for evaluation.",
    }


def assess_fields(fields: set[str]) -> dict[str, Any]:
    present = set(fields)
    missing_full = sorted(set(FULL_ENGINE_REQUIRED_FIELDS) - present)
    caps = []
    for cap in CAPABILITIES:
        missing = sorted(set(cap.fields) - present)
        caps.append({
            "code": cap.code,
            "label": cap.label,
            "ready": not missing,
            "missing_fields": missing,
        })
    return {
        "full_engine_ready": not missing_full,
        "missing_full_engine_fields": missing_full,
        "capabilities": caps,
    }
