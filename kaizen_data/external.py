from __future__ import annotations

import statistics
import uuid
from collections import Counter
from typing import Any

from kaizen_factory.models import FactoryConfig, SimulationResult


def _summary(records: list[dict[str, Any]], activation_unit: int) -> dict[str, Any]:
    def block(rows: list[dict[str, Any]]) -> dict[str, Any]:
        n = max(1, len(rows))
        return {
            "units": len(rows),
            "observed_defect_rate": round(sum(int(r["observed_defect"]) for r in rows) / n, 5),
            "rework_rate": round(sum(int(r["rework"]) for r in rows) / n, 5),
            "avg_queue_wait_s": round(statistics.fmean(float(r["queue_wait_s"]) for r in rows), 3) if rows else 0.0,
            "avg_calibration_s": round(statistics.fmean(float(r["calibration_s"]) for r in rows), 3) if rows else 0.0,
            "avg_unit_flow_time_s": round(
                statistics.fmean(float(r["total_processing_s"]) + float(r["queue_wait_s"]) for r in rows), 3
            ) if rows else 0.0,
            "copq_usd": round(sum(float(r["copq_usd"]) for r in rows), 2),
        }

    pre = records[:activation_unit]
    post = records[activation_unit:]
    return {"pre_incident": block(pre), "post_incident": block(post)}


def build_external_result(
    records: list[dict[str, Any]],
    *,
    activation_unit: int,
    line_name: str,
    source_mode: str,
    source_metadata: dict[str, Any] | None = None,
) -> SimulationResult:
    n = len(records)
    if n < 100:
        raise ValueError("External full-engine runs require at least 100 canonical records.")
    if activation_unit < max(1, int(0.05 * n)) or activation_unit > min(n - 1, int(0.95 * n)):
        raise ValueError("activation_unit must lie between 5% and 95% of the external record sequence.")
    mode = source_mode.upper()
    if mode not in {"FILE", "REPLAY", "LIVE"}:
        raise ValueError("External source_mode must be FILE, REPLAY or LIVE.")
    start_time = str(records[0]["timestamp"])
    config = FactoryConfig(
        seed=0,
        units=n,
        start_time=start_time,
        activation_fraction=activation_unit / n,
        line_name=line_name,
    )
    summary = _summary(records, activation_unit)
    defects = Counter(str(r["defect_type"]) for r in records if r["observed_defect"])
    public_summary = {
        **summary,
        "symptom": "External production data loaded. KAIZEN will compare the declared pre/post boundary without assuming a causal mechanism.",
        "affected_step_hint": "External source — infer from observable records",
        "top_observed_defects": defects.most_common(5),
        "observable_schema": "kaizen-manufacturing-data-contract-v1",
    }
    metadata = dict(source_metadata or {})
    metadata.update({
        "ground_truth_available": False,
        "synthetic_doe_available": False,
        "reveal_scoring_available": False,
    })
    return SimulationResult(
        run_id="EXT-" + uuid.uuid4().hex[:10].upper(),
        config=config,
        scenario_code="EXTERNAL_NO_TRUTH",
        activation_unit=activation_unit,
        public_summary=public_summary,
        records=records,
        latent_records=[],
        ground_truth={},
        source_mode=mode,
        source_metadata=metadata,
    )
