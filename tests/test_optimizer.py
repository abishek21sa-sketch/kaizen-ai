from fastapi.testclient import TestClient

from app.main import app
from kaizen_factory.models import FactoryConfig
from kaizen_factory.simulator import simulate_factory
from kaizen_optimizer import solve_improvement_portfolio

client = TestClient(app)


def test_seed42_optimizer_selects_m2_tool_recalibration_under_default_constraints():
    result = simulate_factory(FactoryConfig(seed=42, units=900), "tool_calibration_drift")
    o = solve_improvement_portfolio(result.records, result.activation_unit)
    assert o["solver"]["status"] == "OPTIMAL_EXACT_SEARCH"
    assert o["solver"]["search_space_size"] == 64
    assert "TOOL_RECALIBRATION" in o["solver"]["eligible_intervention_codes"]
    assert o["best_portfolio"]["intervention_codes"] == ["TOOL_RECALIBRATION"]
    assert o["best_portfolio"]["counterfactual"]["good_throughput_units_per_hour"] >= 80.0
    assert o["best_financials"]["first_year_net_value_usd"] > 0
    assert o["best_portfolio"]["ground_truth_dependency"] is False


def test_optimizer_respects_budget_downtime_and_evidence_gate():
    result = simulate_factory(FactoryConfig(seed=42, units=700), "fixture_wear_temp")
    o = solve_improvement_portfolio(
        result.records, result.activation_unit,
        budget_usd=5000, max_downtime_hours=2.0, min_good_throughput_uph=0,
    )
    assert o["best_portfolio"] is not None
    assert o["best_portfolio"]["engineering_assumptions"]["total_one_time_cost_usd"] <= 5000
    assert o["best_portfolio"]["engineering_assumptions"]["total_planned_downtime_hours"] <= 2.0
    # The high-evidence fixture action costs 9800, so under this budget it cannot be selected.
    assert "FIXTURE_REPLACEMENT_THERMAL" not in o["best_portfolio"]["intervention_codes"]


def test_optimizer_can_return_infeasible_for_unreachable_good_throughput():
    result = simulate_factory(FactoryConfig(seed=42, units=700), "tool_calibration_drift")
    o = solve_improvement_portfolio(
        result.records, result.activation_unit,
        min_good_throughput_uph=500.0,
    )
    assert o["solver"]["status"] == "INFEASIBLE"
    assert o["best_portfolio"] is None
    assert o["infeasibility"]["message"]


def test_optimizer_api_is_available_before_reveal_and_unchanged_after_reveal():
    created = client.post("/api/runs", json={"seed":42,"units":700,"scenario":"tool_calibration_drift"}).json()
    run_id = created["run_id"]
    before = client.get(f"/api/runs/{run_id}/optimizer/overview")
    assert before.status_code == 200
    assert before.json()["truth_revealed"] is False
    assert client.get(f"/api/runs/{run_id}/ground-truth").status_code == 403
    client.post(f"/api/runs/{run_id}/arena/reveal-score")
    after = client.get(f"/api/runs/{run_id}/optimizer/overview")
    assert after.status_code == 200
    assert before.json()["optimizer"] == after.json()["optimizer"]


def test_optimizer_solve_endpoint_and_frontend_hooks():
    created = client.post("/api/runs", json={"seed":42,"units":700,"scenario":"tool_calibration_drift"}).json()
    run_id = created["run_id"]
    r = client.post(f"/api/runs/{run_id}/optimizer/solve", json={
        "budget_usd":25000,
        "max_downtime_hours":8,
        "min_good_throughput_uph":80,
        "max_defect_rate":1.0,
        "annual_volume_units":200000,
        "effectiveness":1.0,
        "demand_multiplier":1.0,
        "min_evidence_score":25,
    })
    assert r.status_code == 200
    o = r.json()["optimizer"]
    assert o["solver"]["status"] == "OPTIMAL_EXACT_SEARCH"
    assert o["best_portfolio"]["engineering_assumptions"]["total_one_time_cost_usd"] <= 25000
    assert o["evidence_state"]["causal_confirmation_unlocked"] is False

    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    html = (root / "static" / "index.html").read_text(encoding="utf-8")
    js = (root / "static" / "app.js").read_text(encoding="utf-8")
    assert "DECIDE / IMPROVEMENT PORTFOLIO OPTIMIZER" in html
    assert "OPTIMIZE PORTFOLIO" in html
    assert "loadOptimizerOverview" in js
    assert "/optimizer/solve" in js
