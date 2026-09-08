from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kaizen_factory.models import FactoryConfig
from kaizen_factory.simulator import simulate_factory
from kaizen_investigator import build_investigation_overview

EXPECTED = {
    "tool_calibration_drift": {
        "code": "MACHINE_TORQUE_BIAS", "target": "M2", "direction": "INCREASE", "interaction": None,
    },
    "fixture_wear_temp": {
        "code": "FIXTURE_ENVIRONMENT_INTERACTION", "target": "F4", "direction": "INCREASE", "interaction": "ambient_temp_c",
    },
    "supplier_resin_shift": {
        "code": "SUPPLIER_HUMIDITY_INTERACTION", "target_prefix": "S2-", "direction": "DECREASE", "interaction": "humidity_pct",
    },
    "gage_measurement_drift": {
        "code": "GAGE_MEASUREMENT_DRIFT", "target": "G2", "direction": "INCREASE", "interaction": None,
    },
    "calibration_microstops": {
        "code": "CALIBRATION_INTERMITTENT_LOSS", "target": "Calibration", "direction": "INCREASE", "interaction": None,
    },
    "changeover_deterioration": {
        "code": "SEQUENCE_CHANGEOVER_LOSS", "target": "Calibration product transitions", "direction": "INCREASE", "interaction": "product_transition",
    },
}


def _target_ok(target: str, expected: dict) -> bool:
    if "target" in expected:
        return target == expected["target"]
    return target.startswith(expected.get("target_prefix", ""))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the V0.5 blind mechanism + full-attribution benchmark.")
    parser.add_argument("--units", type=int, default=900)
    parser.add_argument("--seeds", type=int, nargs="*", default=[3, 7, 17, 42, 113, 2718])
    args = parser.parse_args()

    family_correct = 0
    asset_correct = 0
    full_correct = 0
    total = 0
    confusion: Counter[tuple[str, str]] = Counter()
    print("seed\tscenario\texpected_code\tpredicted_code\ttarget\tdirection\tinteraction\tfamily\tasset\tfull")
    for seed in args.seeds:
        for scenario, expected in EXPECTED.items():
            run = simulate_factory(FactoryConfig(seed=seed, units=args.units), scenario)
            inv = build_investigation_overview(run.records, run.activation_unit)
            top = inv["top_suspect"]
            predicted = top["code"]
            target = str(top["target"])
            attribution = top.get("attribution") or {}
            direction = attribution.get("direction")
            interaction = attribution.get("interaction_partner")

            family_ok = predicted == expected["code"]
            target_ok = _target_ok(target, expected)
            direction_ok = direction == expected["direction"]
            interaction_ok = interaction == expected["interaction"]
            asset_ok = family_ok and target_ok
            full_ok = asset_ok and direction_ok and interaction_ok

            family_correct += int(family_ok)
            asset_correct += int(asset_ok)
            full_correct += int(full_ok)
            total += 1
            confusion[(expected["code"], predicted)] += 1
            print(
                f"{seed}\t{scenario}\t{expected['code']}\t{predicted}\t{target}\t{direction}\t{interaction}\t"
                f"{'PASS' if family_ok else 'MISS'}\t{'PASS' if asset_ok else 'MISS'}\t{'PASS' if full_ok else 'MISS'}"
            )

    print(f"\nTop-1 mechanism-family accuracy: {family_correct}/{total} = {family_correct/total:.3%}")
    print(f"Mechanism + affected-target accuracy: {asset_correct}/{total} = {asset_correct/total:.3%}")
    print(f"Full attribution (family + target + direction + interaction) accuracy: {full_correct}/{total} = {full_correct/total:.3%}")
    print("Synthetic Hidden Factory benchmark only; not a real-factory accuracy claim.")
    return 0 if full_correct == total else 2


if __name__ == "__main__":
    raise SystemExit(main())
