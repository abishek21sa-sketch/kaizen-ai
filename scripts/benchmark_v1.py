from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kaizen_control import build_control_plan
from kaizen_factory.models import FactoryConfig
from kaizen_factory.scenarios import FAULT_CATALOG
from kaizen_factory.simulator import simulate_factory
from kaizen_optimizer import solve_improvement_portfolio


def main() -> None:
    seeds = [11, 42, 73]
    cases = []
    for scenario in FAULT_CATALOG:
        for seed in seeds:
            r = simulate_factory(FactoryConfig(seed=seed, units=700), scenario, reveal_truth=True)
            o = solve_improvement_portfolio(r.records, r.activation_unit)
            c = build_control_plan(r.records, r.activation_unit, line_name=r.config.line_name, seed=r.config.seed)
            cases.append({
                "scenario": scenario,
                "seed": seed,
                "optimizer_status": o["solver"]["status"],
                "milp_status": o["solver"]["milp"]["status"],
                "milp_oracle_agreement": o["solver"]["oracle_agreement"],
                "control_plan_ready": c["state"] == "CONTROL_PLAN_READY",
                "realized_benefits_fabricated": c["handoff"]["realized_benefits_verified"],
            })
    result = {
        "benchmark": "KAIZEN AI V1.0 OR/data/control release gate",
        "scope_note": "Synthetic Hidden Factory release benchmark only; not a real-factory performance estimate.",
        "cases": len(cases),
        "milp_optimal_or_matching_infeasible": sum(x["milp_status"] in {"OPTIMAL", "INFEASIBLE"} for x in cases),
        "milp_exact_oracle_agreement": sum(bool(x["milp_oracle_agreement"]) for x in cases),
        "control_plan_ready": sum(x["control_plan_ready"] for x in cases),
        "fabricated_realized_benefit_cases": sum(bool(x["realized_benefits_fabricated"]) for x in cases),
        "details": cases,
    }
    path = ROOT / "docs" / "V1.0_BENCHMARK.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k != "details"}, indent=2))

if __name__ == "__main__":
    main()
