from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kaizen_factory.models import FactoryConfig
from kaizen_factory.simulator import simulate_factory
from kaizen_optimizer import solve_improvement_portfolio

EXPECTED = {
    "tool_calibration_drift": "TOOL_RECALIBRATION",
    "gage_measurement_drift": "GAGE_RECALIBRATION",
    "fixture_wear_temp": "FIXTURE_REPLACEMENT_THERMAL",
    "supplier_resin_shift": "SUPPLIER_CONTAINMENT",
    "calibration_microstops": "CALIBRATION_SENSOR_SERVICE",
    "changeover_deterioration": "CHANGEOVER_STANDARD_WORK",
}
SEEDS = [7, 42, 88]


def main() -> int:
    cases=[]; match=0; constraints_ok=0
    for scenario, expected in EXPECTED.items():
        for seed in SEEDS:
            result=simulate_factory(FactoryConfig(seed=seed,units=700),scenario)
            o=solve_improvement_portfolio(result.records,result.activation_unit,min_good_throughput_uph=0)
            selected=o["best_portfolio"]["intervention_codes"] if o["best_portfolio"] else []
            ok=expected in selected
            c_ok=(o["best_portfolio"] is not None and
                  o["best_portfolio"]["engineering_assumptions"]["total_one_time_cost_usd"] <= 25000 and
                  o["best_portfolio"]["engineering_assumptions"]["total_planned_downtime_hours"] <= 8)
            match += int(ok); constraints_ok += int(c_ok)
            cases.append({"scenario":scenario,"seed":seed,"expected":expected,"selected":selected,"match":ok,"constraints_ok":c_ok})
    out={
        "benchmark":"V0.7 synthetic constrained-optimizer benchmark",
        "incidents":len(cases),
        "expected_action_in_optimal_portfolio":match,
        "hard_constraints_satisfied":constraints_ok,
        "note":"Synthetic Hidden Factory benchmark only; not a real-plant financial or causal-effectiveness claim.",
        "cases":cases,
    }
    dest=ROOT/'docs'/'V0.7_BENCHMARK.json'; dest.write_text(json.dumps(out,indent=2),encoding='utf-8')
    print(f"Expected action in optimum: {match}/{len(cases)}")
    print(f"Hard constraints satisfied: {constraints_ok}/{len(cases)}")
    print(dest)
    return 0 if match==len(cases) and constraints_ok==len(cases) else 1

if __name__=='__main__':
    raise SystemExit(main())
