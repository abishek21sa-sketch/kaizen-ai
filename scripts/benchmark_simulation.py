from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kaizen_factory.models import FactoryConfig
from kaizen_factory.simulator import simulate_factory
from kaizen_investigator import build_investigation_overview
from kaizen_simulation import run_what_if
from kaizen_simulation.engine import HYPOTHESIS_TO_INTERVENTION

EXPECTED = {
    "tool_calibration_drift": ("TOOL_RECALIBRATION", "quality"),
    "gage_measurement_drift": ("GAGE_RECALIBRATION", "quality"),
    "fixture_wear_temp": ("FIXTURE_REPLACEMENT_THERMAL", "quality"),
    "supplier_resin_shift": ("SUPPLIER_CONTAINMENT", "quality"),
    "calibration_microstops": ("CALIBRATION_SENSOR_SERVICE", "flow"),
    "changeover_deterioration": ("CHANGEOVER_STANDARD_WORK", "flow"),
}
SEEDS = [7, 42, 88]


def main() -> int:
    rows = []
    recommendation_ok = 0
    outcome_ok = 0
    for scenario, (expected_intervention, domain) in EXPECTED.items():
        for seed in SEEDS:
            result = simulate_factory(FactoryConfig(seed=seed, units=700), scenario)
            inv = build_investigation_overview(result.records, result.activation_unit)
            recommended = HYPOTHESIS_TO_INTERVENTION[inv["top_suspect"]["code"]]
            w = run_what_if(result.records, result.activation_unit, recommended)
            rec_ok = recommended == expected_intervention
            if domain == "quality":
                benefit_ok = w["counterfactual"]["defect_rate"] <= w["baseline"]["defect_rate"] and w["counterfactual"]["copq_per_1000_units_usd"] <= w["baseline"]["copq_per_1000_units_usd"]
            else:
                benefit_ok = w["counterfactual"]["mean_queue_wait_s"] <= w["baseline"]["mean_queue_wait_s"] and w["counterfactual"]["mean_lead_time_s"] <= w["baseline"]["mean_lead_time_s"]
            recommendation_ok += int(rec_ok)
            outcome_ok += int(benefit_ok)
            rows.append({
                "scenario": scenario,
                "seed": seed,
                "expected_intervention": expected_intervention,
                "recommended_intervention": recommended,
                "recommendation_match": rec_ok,
                "expected_domain": domain,
                "outcome_improves_expected_domain": benefit_ok,
                "defect_rate_before": w["baseline"]["defect_rate"],
                "defect_rate_after": w["counterfactual"]["defect_rate"],
                "queue_wait_before_s": w["baseline"]["mean_queue_wait_s"],
                "queue_wait_after_s": w["counterfactual"]["mean_queue_wait_s"],
                "copq_before_per_1000": w["baseline"]["copq_per_1000_units_usd"],
                "copq_after_per_1000": w["counterfactual"]["copq_per_1000_units_usd"],
            })
    out = {
        "benchmark": "V0.6 synthetic paired-counterfactual benchmark",
        "incidents": len(rows),
        "recommendation_match": recommendation_ok,
        "expected_domain_improvement": outcome_ok,
        "note": "Synthetic Hidden Factory benchmark only; not a real-factory effectiveness claim.",
        "cases": rows,
    }
    dest = ROOT / "docs" / "V0.6_BENCHMARK.json"
    dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Recommendation match: {recommendation_ok}/{len(rows)}")
    print(f"Expected-domain improvement: {outcome_ok}/{len(rows)}")
    print(dest)
    return 0 if recommendation_ok == len(rows) and outcome_ok == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
