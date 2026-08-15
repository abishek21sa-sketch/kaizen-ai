from fastapi.testclient import TestClient

from app.main import app
from kaizen_factory.models import FactoryConfig
from kaizen_factory.simulator import simulate_factory
from kaizen_simulation import build_simulation_overview, run_what_if

client = TestClient(app)


def test_seed42_recommends_tool_recalibration_and_improves_quality():
    result = simulate_factory(FactoryConfig(seed=42, units=900), "tool_calibration_drift")
    overview = build_simulation_overview(result.records, result.activation_unit)
    assert overview["recommended_intervention_code"] == "TOOL_RECALIBRATION"
    w = overview["recommended_intervention"]
    assert w["diagnostic_basis"]["target"] == "M2"
    assert w["counterfactual"]["defect_rate"] < w["baseline"]["defect_rate"]
    assert w["counterfactual"]["copq_per_1000_units_usd"] < w["baseline"]["copq_per_1000_units_usd"]
    assert w["ground_truth_dependency"] is False


def test_microstop_service_reduces_queue_wait():
    result = simulate_factory(FactoryConfig(seed=42, units=900), "calibration_microstops")
    w = run_what_if(result.records, result.activation_unit, "CALIBRATION_SENSOR_SERVICE")
    assert w["counterfactual"]["mean_queue_wait_s"] < w["baseline"]["mean_queue_wait_s"]
    assert w["counterfactual"]["mean_lead_time_s"] < w["baseline"]["mean_lead_time_s"]


def test_changeover_standard_work_reduces_flow_penalty():
    result = simulate_factory(FactoryConfig(seed=1, units=1200), "changeover_deterioration")
    w = run_what_if(result.records, result.activation_unit, "CHANGEOVER_STANDARD_WORK")
    assert w["counterfactual"]["mean_queue_wait_s"] < w["baseline"]["mean_queue_wait_s"]
    assert w["delta"]["copq_per_1000_units_usd"] < 0


def test_demand_multiplier_stresses_same_paired_replay():
    result = simulate_factory(FactoryConfig(seed=42, units=900), "tool_calibration_drift")
    normal = run_what_if(result.records, result.activation_unit, "TOOL_RECALIBRATION", demand_multiplier=1.0)
    high = run_what_if(result.records, result.activation_unit, "TOOL_RECALIBRATION", demand_multiplier=1.5)
    assert high["baseline"]["mean_queue_wait_s"] >= normal["baseline"]["mean_queue_wait_s"]
    assert high["settings"]["demand_multiplier"] == 1.5


def test_simulation_api_is_identical_before_and_after_reveal():
    created = client.post("/api/runs", json={"seed":42,"units":700,"scenario":"tool_calibration_drift"}).json()
    run_id = created["run_id"]
    before = client.get(f"/api/runs/{run_id}/simulation/overview")
    assert before.status_code == 200
    assert client.get(f"/api/runs/{run_id}/ground-truth").status_code == 403
    client.post(f"/api/runs/{run_id}/arena/reveal-score")
    after = client.get(f"/api/runs/{run_id}/simulation/overview")
    assert after.status_code == 200
    assert before.json()["simulation"] == after.json()["simulation"]


def test_simulation_what_if_api_validation_and_frontend_hooks():
    created = client.post("/api/runs", json={"seed":42,"units":700,"scenario":"tool_calibration_drift"}).json()
    run_id = created["run_id"]
    r = client.post(f"/api/runs/{run_id}/simulation/what-if", json={
        "intervention_code":"TOOL_RECALIBRATION", "effectiveness":0.8, "demand_multiplier":1.1
    })
    assert r.status_code == 200
    body = r.json()["what_if"]
    assert body["settings"] == {"effectiveness":0.8,"demand_multiplier":1.1}
    bad = client.post(f"/api/runs/{run_id}/simulation/what-if", json={
        "intervention_code":"BOGUS", "effectiveness":1.0, "demand_multiplier":1.0
    })
    assert bad.status_code == 422

    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    html = (root / "static" / "index.html").read_text(encoding="utf-8")
    js = (root / "static" / "app.js").read_text(encoding="utf-8")
    assert "IMPROVE / PROCESS SIMULATION" in html
    assert "RUN WHAT-IF" in html
    assert "loadSimulationOverview" in js
    assert "/simulation/what-if" in js
