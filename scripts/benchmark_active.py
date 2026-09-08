from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kaizen_active import (
    build_active_investigation_overview,
    build_experiment_design,
    execute_controlled_experiment,
    freeze_human_prediction,
    score_human_prediction,
)
from kaizen_factory.models import FactoryConfig
from kaizen_factory.scenarios import FAULT_CATALOG
from kaizen_factory.simulator import simulate_factory

OUT = ROOT / "docs" / "V0.9_BENCHMARK.json"


def main() -> int:
    seeds = [3, 17, 42]
    rows = []
    for scenario in FAULT_CATALOG:
        for seed in seeds:
            run = simulate_factory(FactoryConfig(seed=seed, units=700), scenario)
            active = build_active_investigation_overview(run.records, run.activation_unit)
            design = build_experiment_design(run.records, run.activation_unit)
            experiment = execute_controlled_experiment(
                run.records, run.activation_unit, run.scenario_code, design["experiment_code"], seed=seed
            )
            human = freeze_human_prediction(run.records, run.activation_unit, active["active_investigation"]["leading_hypothesis"]["code"])
            human_score = score_human_prediction(human, run.scenario_code)
            rows.append({
                "scenario": scenario,
                "seed": seed,
                "uncertainty_state": active["uncertainty"]["state"],
                "leading_hypothesis": active["active_investigation"]["leading_hypothesis"]["code"],
                "recommended_probe": active["value_of_information"]["recommended_next_measurement"]["code"],
                "experiment_code": design["experiment_code"],
                "l5_confirmed": experiment["causal_confirmation"]["passed"],
                "experiment_p_value": experiment["aggregate_results"]["p_value"],
                "experiment_cohen_d": experiment["aggregate_results"]["cohen_d"],
                "reference_human_score": human_score["score"],
            })

    # Deliberate low-information blind runs: this is a policy benchmark, not a diagnosis-accuracy benchmark.
    idk_rows = []
    for seed in range(20):
        run = simulate_factory(FactoryConfig(seed=seed, units=100), "random")
        active = build_active_investigation_overview(run.records, run.activation_unit)
        idk_rows.append({
            "seed": seed,
            "hidden_scenario_not_used_by_policy": True,
            "state": active["uncertainty"]["state"],
            "evidence_score": active["uncertainty"]["evidence_score"],
            "gap": active["uncertainty"]["score_gap"],
        })

    result = {
        "benchmark": "KAIZEN AI V0.9 active investigation / synthetic DOE",
        "scope_note": "Synthetic Hidden Factory benchmark only; not a claim of real-factory causal or diagnostic accuracy.",
        "full_information_cases": len(rows),
        "correct_synthetic_doe_confirmations": sum(int(x["l5_confirmed"]) for x in rows),
        "reference_human_full_attribution": sum(int(x["reference_human_score"] == 100.0) for x in rows),
        "small_blind_cases": len(idk_rows),
        "small_blind_i_dont_know_count": sum(int(x["state"] == "I_DONT_KNOW") for x in idk_rows),
        "full_information_results": rows,
        "small_sample_policy_results": idk_rows,
    }
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k not in {"full_information_results","small_sample_policy_results"}}, indent=2))
    return 0 if result["correct_synthetic_doe_confirmations"] == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
