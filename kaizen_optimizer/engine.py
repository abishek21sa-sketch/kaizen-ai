from __future__ import annotations

import itertools
from typing import Any

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

from kaizen_simulation import INTERVENTION_CATALOG, run_portfolio
from kaizen_investigator import build_investigation_overview


def _portfolio_financials(result: dict[str, Any], annual_volume_units: int) -> dict[str, Any]:
    base = float(result["baseline"]["copq_per_1000_units_usd"])
    cf = float(result["counterfactual"]["copq_per_1000_units_usd"])
    cost = float(result["engineering_assumptions"]["total_one_time_cost_usd"])
    raw_annual_copq_avoided = max(0.0, base - cf) * annual_volume_units / 1000.0
    scores = [float(x.get("evidence_score", 0.0)) for x in result.get("interventions", [])]
    evidence_factor = 1.0 if not scores else min(scores) / 100.0
    evidence_adjusted_benefit = raw_annual_copq_avoided * evidence_factor
    net_first_year = evidence_adjusted_benefit - cost
    roi = None if cost <= 0 else net_first_year / cost
    payback_years = None if evidence_adjusted_benefit <= 0 else cost / evidence_adjusted_benefit
    return {
        "annual_volume_units": annual_volume_units,
        "raw_annual_copq_avoided_usd": round(raw_annual_copq_avoided, 2),
        "evidence_confidence_factor": round(evidence_factor, 4),
        "evidence_adjusted_annual_benefit_usd": round(evidence_adjusted_benefit, 2),
        "annual_copq_avoided_usd": round(raw_annual_copq_avoided, 2),
        "first_year_net_value_usd": round(net_first_year, 2),
        "first_year_roi": None if roi is None else round(roi, 4),
        "simple_payback_years": None if payback_years is None else round(payback_years, 4),
        "monetization_policy": "Only modeled COPQ reduction is monetized. Throughput improvement is a hard constraint. Modeled benefit is conservatively discounted by the weakest selected action's observational evidence score; this is an explicit decision-risk heuristic, not a probability of causality.",
    }


def _candidate_summary(result: dict[str, Any], annual_volume_units: int, constraints: dict[str, float]) -> dict[str, Any]:
    fin = _portfolio_financials(result, annual_volume_units)
    cost = float(result["engineering_assumptions"]["total_one_time_cost_usd"])
    downtime = float(result["engineering_assumptions"]["total_planned_downtime_hours"])
    good = float(result["counterfactual"]["good_throughput_units_per_hour"])
    defect = float(result["counterfactual"]["defect_rate"])
    feasible_flags = {
        "budget": cost <= constraints["budget_usd"] + 1e-9,
        "downtime": downtime <= constraints["max_downtime_hours"] + 1e-9,
        "good_throughput": good + 1e-9 >= constraints["min_good_throughput_uph"],
        "defect_rate": defect <= constraints["max_defect_rate"] + 1e-12,
    }
    return {
        "intervention_codes": result["intervention_codes"],
        "labels": [x["label"] for x in result["interventions"]],
        "cost_usd": round(cost, 2),
        "downtime_hours": round(downtime, 3),
        "good_throughput_uph": round(good, 4),
        "defect_rate": round(defect, 6),
        "copq_per_1000_usd": result["counterfactual"]["copq_per_1000_units_usd"],
        "delta_copq_per_1000_usd": result["delta"]["copq_per_1000_units_usd"],
        "delta_good_throughput_uph": result["delta"]["good_throughput_units_per_hour"],
        "financials": fin,
        "feasible": all(feasible_flags.values()),
        "constraint_checks": feasible_flags,
    }



def _solve_exact_selection_milp(candidates: list[dict[str, Any]], constraints: dict[str, float]) -> dict[str, Any]:
    """Solve exact portfolio selection as a binary MILP over simulated portfolio outcomes.

    The nonlinear counterfactual engine is evaluated before this optimization. Each candidate
    portfolio becomes one binary selection variable y_j. This preserves the exact simulated
    portfolio metrics while expressing the managerial decision as a formal MILP. Exhaustive
    enumeration remains an independent oracle at the current six-action scale.
    """
    if not candidates:
        return {
            "status": "INFEASIBLE", "success": False, "selected_index": None,
            "selected_intervention_codes": [], "objective_first_year_net_value_usd": None,
            "message": "No candidates were available to the MILP.",
        }
    n = len(candidates)
    net = np.array([float(x["financials"]["first_year_net_value_usd"]) for x in candidates], dtype=float)
    cost = np.array([float(x["cost_usd"]) for x in candidates], dtype=float)
    dt = np.array([float(x["downtime_hours"]) for x in candidates], dtype=float)
    good = np.array([float(x["good_throughput_uph"]) for x in candidates], dtype=float)
    defect = np.array([float(x["defect_rate"]) for x in candidates], dtype=float)

    # scipy.optimize.milp minimizes c @ x, hence negative net value.
    c = -net
    A = np.vstack([np.ones(n), cost, dt, good, defect])
    lb = np.array([1.0, -np.inf, -np.inf, constraints["min_good_throughput_uph"], -np.inf])
    ub = np.array([1.0, constraints["budget_usd"], constraints["max_downtime_hours"], np.inf, constraints["max_defect_rate"]])
    res = milp(
        c=c,
        integrality=np.ones(n, dtype=int),
        bounds=Bounds(np.zeros(n), np.ones(n)),
        constraints=LinearConstraint(A, lb, ub),
        options={"presolve": True},
    )
    if not res.success or res.x is None:
        return {
            "status": "INFEASIBLE" if int(res.status) == 2 else "SOLVER_ERROR",
            "success": False,
            "selected_index": None,
            "selected_intervention_codes": [],
            "objective_first_year_net_value_usd": None,
            "scipy_status": int(res.status),
            "message": str(res.message),
        }
    idx = int(np.argmax(res.x))
    chosen = candidates[idx]
    return {
        "status": "OPTIMAL",
        "success": True,
        "selected_index": idx,
        "selected_intervention_codes": list(chosen["intervention_codes"]),
        "objective_first_year_net_value_usd": float(chosen["financials"]["first_year_net_value_usd"]),
        "scipy_status": int(res.status),
        "message": str(res.message),
        "binary_variables": n,
        "formulation": "One binary y_j per precomputed counterfactual portfolio; choose exactly one portfolio while enforcing budget, downtime, minimum good-throughput and maximum-defect constraints.",
    }

def solve_improvement_portfolio(
    records: list[dict[str, Any]],
    activation_unit: int,
    *,
    budget_usd: float = 25_000.0,
    max_downtime_hours: float = 8.0,
    min_good_throughput_uph: float = 80.0,
    max_defect_rate: float = 1.0,
    annual_volume_units: int = 200_000,
    effectiveness: float = 1.0,
    demand_multiplier: float = 1.0,
    min_evidence_score: float = 25.0,
) -> dict[str, Any]:
    if budget_usd < 0:
        raise ValueError("budget_usd must be non-negative")
    if max_downtime_hours < 0:
        raise ValueError("max_downtime_hours must be non-negative")
    if min_good_throughput_uph < 0:
        raise ValueError("min_good_throughput_uph must be non-negative")
    if not 0 <= max_defect_rate <= 1:
        raise ValueError("max_defect_rate must be between 0 and 1")
    if annual_volume_units <= 0:
        raise ValueError("annual_volume_units must be positive")
    if not 0 <= effectiveness <= 1:
        raise ValueError("effectiveness must be between 0 and 1")
    if not 0.5 <= demand_multiplier <= 1.75:
        raise ValueError("demand_multiplier must be between 0.5 and 1.75")
    if not 0 <= min_evidence_score <= 100:
        raise ValueError("min_evidence_score must be between 0 and 100")

    constraints = {
        "budget_usd": float(budget_usd),
        "max_downtime_hours": float(max_downtime_hours),
        "min_good_throughput_uph": float(min_good_throughput_uph),
        "max_defect_rate": float(max_defect_rate),
        "min_evidence_score": float(min_evidence_score),
    }
    codes = list(INTERVENTION_CATALOG)
    inv = build_investigation_overview(records, activation_unit)
    hmap = {h["code"]: h for h in inv["ranked_hypotheses"]}
    candidates: list[dict[str, Any]] = []
    pruned_static = 0
    evaluated = 0
    eligible_codes = {
        code for code in codes
        if float(hmap[INTERVENTION_CATALOG[code]["hypothesis_code"]]["evidence_score"]) >= min_evidence_score
    }
    for r in range(len(codes) + 1):
        for combo in itertools.combinations(codes, r):
            static_cost = sum(float(INTERVENTION_CATALOG[c]["one_time_cost_usd"]) for c in combo)
            static_dt = sum(float(INTERVENTION_CATALOG[c]["planned_downtime_hours"]) for c in combo)
            evidence_ok = all(c in eligible_codes for c in combo)
            if static_cost > budget_usd + 1e-9 or static_dt > max_downtime_hours + 1e-9 or not evidence_ok:
                pruned_static += 1
                continue
            result = run_portfolio(
                records, activation_unit, list(combo),
                effectiveness=effectiveness,
                demand_multiplier=demand_multiplier,
                bootstrap=False,
                _hmap=hmap, _inv=inv,
            )
            evaluated += 1
            summary = _candidate_summary(result, annual_volume_units, constraints)
            candidates.append(summary)

    feasible = [x for x in candidates if x["feasible"]]
    # Objective: maximize first-year net COPQ value. Tie-breakers prefer lower cost,
    # higher good throughput, then fewer interventions for implementability.
    feasible.sort(key=lambda x: (
        x["financials"]["first_year_net_value_usd"],
        -x["cost_usd"],
        x["good_throughput_uph"],
        -len(x["intervention_codes"]),
    ), reverse=True)

    milp_result = _solve_exact_selection_milp(candidates, constraints)

    if feasible:
        best_summary = feasible[0]
        key = tuple(best_summary["intervention_codes"])
        best = run_portfolio(
            records, activation_unit, list(key),
            effectiveness=effectiveness,
            demand_multiplier=demand_multiplier,
            bootstrap=True,
            _hmap=hmap, _inv=inv,
        )
        best_fin = _portfolio_financials(best, annual_volume_units)
        solver_status = "OPTIMAL_EXACT_SEARCH"
        infeasibility = None
    else:
        best_summary = None
        best = None
        best_fin = None
        solver_status = "INFEASIBLE"
        # Surface the portfolios closest to satisfying the requested operational constraints.
        def violation_score(x: dict[str, Any]) -> float:
            score = 0.0
            score += max(0.0, x["cost_usd"] - budget_usd) / max(1.0, budget_usd)
            score += max(0.0, x["downtime_hours"] - max_downtime_hours) / max(1.0, max_downtime_hours)
            score += max(0.0, min_good_throughput_uph - x["good_throughput_uph"]) / max(1.0, min_good_throughput_uph)
            score += max(0.0, x["defect_rate"] - max_defect_rate) / max(0.01, max_defect_rate)
            return score
        nearest = sorted(candidates, key=violation_score)[:5]
        infeasibility = {
            "message": "No intervention portfolio satisfies all hard constraints.",
            "nearest_portfolios": nearest,
        }

    return {
        "version": "optimizer-v1.0",
        "solver": {
            "method": "MILP portfolio selection + exhaustive nonlinear oracle",
            "decision_variables": {code: "binary intervention membership in the portfolio" for code in codes},
            "milp_selection_variables": "one binary y_j per counterfactually evaluated candidate portfolio",
            "search_space_size": 2 ** len(codes),
            "evaluated_portfolios": evaluated,
            "pruned_by_static_or_evidence_constraints": pruned_static,
            "eligible_intervention_codes": sorted(eligible_codes),
            "status": solver_status,
            "milp": milp_result,
            "oracle_agreement": (
                (not feasible and not milp_result.get("success"))
                or (bool(feasible) and milp_result.get("success") and abs(float(feasible[0]["financials"]["first_year_net_value_usd"]) - float(milp_result.get("objective_first_year_net_value_usd", float("nan")))) < 0.01)
            ),
            "optimality_statement": "V1.0 evaluates the nonlinear counterfactual outcomes for the current six-action catalog, solves the constrained portfolio choice as a binary MILP, and independently checks the result against exhaustive enumeration. The released recommendation uses the exact nonlinear oracle at this small scale; MILP/oracle agreement is reported explicitly.",
            "scale_note": "The current exact nonlinear oracle is intentionally retained because 2^6=64 is tiny. Larger action catalogs require an action-level MILP/decomposition or surrogate interaction model; KAIZEN does not claim that precomputing 2^n portfolios scales indefinitely.",
        },
        "objective": {
            "name": "MAX_EVIDENCE_ADJUSTED_FIRST_YEAR_NET_VALUE",
            "definition": "raw annual modeled COPQ avoided × weakest-selected-action evidence factor - one-time intervention cost",
            "throughput_policy": "Good throughput is a hard constraint, not monetized in the objective.",
            "evidence_policy": "The weakest selected action evidence score discounts modeled benefit. Evidence scores remain ranking indices, not probabilities; the discount is a transparent decision-risk heuristic.",
        },
        "constraints": constraints | {
            "annual_volume_units": annual_volume_units,
            "effectiveness": effectiveness,
            "demand_multiplier": demand_multiplier,
            "min_evidence_score": min_evidence_score,
        },
        "best_portfolio": best,
        "best_financials": best_fin,
        "top_feasible_portfolios": feasible[:8],
        "feasible_portfolio_count": len(feasible),
        "infeasibility": infeasibility,
        "evidence_state": {
            "optimizer_core": "MILP_AND_EXACT_ORACLE_IMPLEMENTED_AND_TESTED",
            "ground_truth_dependency": False,
            "causal_confirmation_unlocked": False,
            "note": "V1.0 solves the modeled intervention choice with a binary MILP and independently validates it against exact nonlinear enumeration at the six-action scale. The optimum remains conditional on the simulation model and observational diagnosis, not causal proof.",
        },
    }


def build_optimizer_overview(records: list[dict[str, Any]], activation_unit: int) -> dict[str, Any]:
    return solve_improvement_portfolio(records, activation_unit)
