from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kaizen_arena.engine import EXPECTED_ATTRIBUTION, score_revealed_diagnosis
from kaizen_factory.models import FactoryConfig
from kaizen_factory.simulator import simulate_factory


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the V0.5 blind diagnosis + post-reveal attribution scoring harness.")
    parser.add_argument("--units", type=int, default=900)
    parser.add_argument("--seeds", type=int, nargs="*", default=[3, 7, 17, 42, 113, 2718])
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    rows = []
    for seed in args.seeds:
        for scenario in EXPECTED_ATTRIBUTION:
            result = simulate_factory(FactoryConfig(seed=seed, units=args.units), scenario)
            card = score_revealed_diagnosis(
                result.records, result.activation_unit, result.scenario_code, result.ground_truth
            )
            rows.append({
                "seed": seed,
                "scenario": scenario,
                "score": card["score"],
                "grade": card["grade"],
                "checks": card["checks"],
                "prediction": card["blind_prediction"],
                "expected": card["expected_attribution"],
            })

    total = len(rows)
    full = sum(r["grade"] == "FULL_ATTRIBUTION_MATCH" for r in rows)
    mechanism = sum(r["checks"]["mechanism_family"] for r in rows)
    target = sum(r["checks"]["mechanism_family"] and r["checks"]["affected_target"] for r in rows)
    summary = {
        "units_per_incident": args.units,
        "seeds": args.seeds,
        "incident_count": total,
        "mechanism_family_correct": mechanism,
        "mechanism_plus_target_correct": target,
        "full_attribution_correct": full,
        "full_attribution_rate": full / total if total else 0.0,
        "scope_note": "Deterministic synthetic Hidden Factory benchmark only; not a real-factory accuracy estimate.",
        "rows": rows,
    }

    print(f"V0.5 arena benchmark: {total} blind incidents")
    print(f"Mechanism family: {mechanism}/{total}")
    print(f"Mechanism + target: {target}/{total}")
    print(f"Full attribution: {full}/{total}")
    print(summary["scope_note"])

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"Wrote {args.json_out}")
    return 0 if full == total else 2


if __name__ == "__main__":
    raise SystemExit(main())
