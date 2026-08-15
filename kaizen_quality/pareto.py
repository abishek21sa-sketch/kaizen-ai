from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

QUALITY_REWORK_COST = 46.0
QUALITY_SCRAP_COST = 215.0


def pareto_and_copq(records: list[dict[str, Any]]) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    allocated_cost: defaultdict[str, float] = defaultdict(float)
    rework_units = 0
    scrap_units = 0
    quality_copq = 0.0
    flow_copq = 0.0

    for r in records:
        row_quality = (QUALITY_REWORK_COST if r["rework"] else 0.0) + (QUALITY_SCRAP_COST if r["scrap"] else 0.0)
        quality_copq += row_quality
        flow_copq += max(0.0, float(r["copq_usd"]) - row_quality)
        rework_units += int(bool(r["rework"]))
        scrap_units += int(bool(r["scrap"]))
        if r["observed_defect"]:
            families = [x for x in str(r["defect_type"]).split("+") if x and x != "NONE"]
            if families:
                share = row_quality / len(families) if row_quality else 0.0
                for family in families:
                    counts[family] += 1
                    allocated_cost[family] += share

    total_occurrences = sum(counts.values())
    ordered = counts.most_common()
    cumulative = 0
    pareto = []
    for family, count in ordered:
        cumulative += count
        pareto.append({
            "defect_family": family,
            "occurrences": count,
            "share": count / max(1, total_occurrences),
            "cumulative_share": cumulative / max(1, total_occurrences),
            "allocated_quality_copq_usd": round(allocated_cost[family], 2),
        })

    total_copq = sum(float(r["copq_usd"]) for r in records)
    return {
        "pareto": pareto,
        "copq": {
            "total_usd": round(total_copq, 2),
            "quality_usd": round(quality_copq, 2),
            "flow_delay_usd": round(flow_copq, 2),
            "per_1000_units_usd": round(total_copq / max(1, len(records)) * 1000, 2),
            "rework_units": rework_units,
            "scrap_units": scrap_units,
            "assumptions": {"rework_cost_usd": QUALITY_REWORK_COST, "scrap_cost_usd": QUALITY_SCRAP_COST},
        },
    }
