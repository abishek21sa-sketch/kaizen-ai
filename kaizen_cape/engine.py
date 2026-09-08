"""CAPE-Loop: Controlled Allocation of Process Experiments.

CAPE-Loop is the portfolio-level experiment-allocation layer for KAIZEN AI. It
allocates scarce experiment resources to competing hypotheses while explicitly
keeping causal confirmation outside the allocator. A high observational score can
prioritize an experiment; it can never unlock the causal gate.
"""
from __future__ import annotations

from typing import Any
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

from kaizen_active import build_active_investigation_overview


def _level_value(base_voi: float, evidence_score: float, rank: int, level: int) -> float:
    if level <= 0:
        return 0.0
    # Diminishing information returns with an ambiguity/evidence-gap premium.
    evidence_gap = max(0.0, 80.0 - evidence_score)
    consequence = max(0.25, 1.0 - 0.10 * (rank - 1))
    marginal = base_voi * consequence * (1.0 + 0.004 * evidence_gap)
    return float(marginal * sum(1.0 / (1.0 + 0.65 * j) for j in range(level)))


def allocate_experiment_portfolio(
    records: list[dict[str, Any]],
    activation_unit: int,
    *,
    budget_usd: float = 900.0,
    max_downtime_hours: float = 2.5,
    max_experiment_runs: int = 4,
    max_replicates_per_hypothesis: int = 2,
) -> dict[str, Any]:
    if budget_usd < 0 or max_downtime_hours < 0 or max_experiment_runs < 0:
        raise ValueError("resource limits must be non-negative")
    if max_replicates_per_hypothesis < 1 or max_replicates_per_hypothesis > 6:
        raise ValueError("max_replicates_per_hypothesis must be between 1 and 6")

    active = build_active_investigation_overview(records, activation_unit)
    candidates = active["value_of_information"]["ranked_candidates"]
    # One-hot level choice per hypothesis: level 0..R. This linearizes diminishing
    # returns while preventing duplicate allocation states.
    levels = list(range(max_replicates_per_hypothesis + 1))
    variables: list[tuple[int, int]] = [(i, level) for i in range(len(candidates)) for level in levels]
    n = len(variables)
    objective = np.zeros(n)
    costs = np.zeros(n)
    hours = np.zeros(n)
    runs = np.zeros(n)
    for j, (i, level) in enumerate(variables):
        c = candidates[i]
        objective[j] = -_level_value(
            float(c["value_of_information_score"]),
            float(c["current_evidence_score"]),
            int(c["hypothesis_rank"]),
            level,
        )
        costs[j] = float(c["cost_usd"]) * level
        hours[j] = float(c["duration_hours"]) * level
        runs[j] = level

    rows = []
    lb = []
    ub = []
    for i in range(len(candidates)):
        row = np.zeros(n)
        for j, pair in enumerate(variables):
            if pair[0] == i:
                row[j] = 1.0
        rows.append(row); lb.append(1.0); ub.append(1.0)
    rows.extend([costs, hours, runs])
    lb.extend([-np.inf, -np.inf, -np.inf])
    ub.extend([budget_usd, max_downtime_hours, float(max_experiment_runs)])

    res = milp(
        c=objective,
        integrality=np.ones(n, dtype=int),
        bounds=Bounds(np.zeros(n), np.ones(n)),
        constraints=LinearConstraint(np.vstack(rows), np.asarray(lb), np.asarray(ub)),
        options={"presolve": True},
    )
    if not res.success or res.x is None:
        return {
            "status": "INFEASIBLE" if int(res.status) == 2 else "SOLVER_ERROR",
            "allocation": [],
            "resource_use": {"budget_usd": 0.0, "downtime_hours": 0.0, "runs": 0},
            "causal_firewall": {
                "causal_confirmation_unlocked": False,
                "policy": "Allocation can prioritize evidence generation but cannot establish causality.",
            },
            "message": str(res.message),
        }

    selected = []
    total_value = 0.0
    for j, x in enumerate(res.x):
        if x < 0.5:
            continue
        i, level = variables[j]
        if level == 0:
            continue
        c = candidates[i]
        value = _level_value(float(c["value_of_information_score"]), float(c["current_evidence_score"]), int(c["hypothesis_rank"]), level)
        total_value += value
        selected.append({
            "hypothesis_code": c["hypothesis_code"],
            "probe_code": c["code"],
            "label": c["label"],
            "replicates": level,
            "allocated_cost_usd": round(float(c["cost_usd"]) * level, 2),
            "allocated_downtime_hours": round(float(c["duration_hours"]) * level, 3),
            "information_priority_value": round(value, 3),
            "observational_evidence_score": c["current_evidence_score"],
        })
    selected.sort(key=lambda x: -x["information_priority_value"])
    return {
        "status": "OPTIMAL",
        "method": "CAPE-Loop binary one-hot MILP with diminishing information returns",
        "allocation": selected,
        "objective_information_priority": round(total_value, 3),
        "resource_use": {
            "budget_usd": round(sum(x["allocated_cost_usd"] for x in selected), 2),
            "downtime_hours": round(sum(x["allocated_downtime_hours"] for x in selected), 3),
            "runs": int(sum(x["replicates"] for x in selected)),
        },
        "resource_limits": {
            "budget_usd": budget_usd,
            "max_downtime_hours": max_downtime_hours,
            "max_experiment_runs": max_experiment_runs,
            "max_replicates_per_hypothesis": max_replicates_per_hypothesis,
        },
        "causal_firewall": {
            "causal_confirmation_unlocked": False,
            "observational_allocation_authority": "PRIORITIZE_EXPERIMENTS_ONLY",
            "unlock_requirement": "Only an authorized controlled experiment that passes its predeclared statistical/effect-size rule may unlock synthetic causal confirmation.",
        },
        "evidence_boundary": "CAPE scores are decision-priority indices, not probabilities of causality or realized economic benefit.",
    }


def build_cape_overview(records: list[dict[str, Any]], activation_unit: int) -> dict[str, Any]:
    return allocate_experiment_portfolio(records, activation_unit)


def allocate_rank_greedy_baseline(
    records: list[dict[str, Any]],
    activation_unit: int,
    *,
    budget_usd: float = 900.0,
    max_downtime_hours: float = 2.5,
    max_experiment_runs: int = 4,
) -> dict[str, Any]:
    """Naive portfolio baseline: take ranked probes one-at-a-time until resources bind.

    This deliberately ignores replicate-level diminishing returns and the joint
    multidimensional knapsack structure. It exists only as a transparent benchmark
    for CAPE-Loop; it has no causal authority.
    """
    active = build_active_investigation_overview(records, activation_unit)
    candidates = list(active["value_of_information"]["ranked_candidates"])
    selected=[]; cost=0.0; hours=0.0; value=0.0; runs=0
    for c in candidates:
        c_cost=float(c["cost_usd"]); c_hours=float(c["duration_hours"])
        if runs + 1 > max_experiment_runs or cost + c_cost > budget_usd + 1e-12 or hours + c_hours > max_downtime_hours + 1e-12:
            continue
        v=_level_value(float(c["value_of_information_score"]),float(c["current_evidence_score"]),int(c["hypothesis_rank"]),1)
        selected.append({
            "hypothesis_code":c["hypothesis_code"],"probe_code":c["code"],"replicates":1,
            "allocated_cost_usd":c_cost,"allocated_downtime_hours":c_hours,
            "information_priority_value":round(v,3),
        })
        cost += c_cost; hours += c_hours; value += v; runs += 1
    return {
        "status":"FEASIBLE_BASELINE",
        "method":"rank-greedy one-replicate baseline",
        "allocation":selected,
        "objective_information_priority":round(value,3),
        "resource_use":{"budget_usd":round(cost,2),"downtime_hours":round(hours,3),"runs":runs},
        "causal_confirmation_unlocked":False,
    }
