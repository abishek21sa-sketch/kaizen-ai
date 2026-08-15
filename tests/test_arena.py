from fastapi.testclient import TestClient

from app.main import app
from kaizen_arena import build_arena_overview, score_revealed_diagnosis
from kaizen_factory.models import FactoryConfig
from kaizen_factory.simulator import simulate_factory

client = TestClient(app)


def test_arena_overview_is_blind_and_contains_timeline():
    result = simulate_factory(FactoryConfig(seed=42, units=700), "tool_calibration_drift")
    arena = build_arena_overview(result.records, result.activation_unit)
    assert arena["truth_available_to_investigator"] is False
    assert arena["prediction_snapshot"]["target"] == "M2"
    assert len(arena["timeline"]) == 6
    assert arena["timeline"][-1]["status"] == "LOCKED"
    serialized = str(arena).lower()
    assert "tool_calibration_drift" not in serialized
    assert "root_cause" not in serialized
    assert "m2_calibration_bias" not in serialized


def test_reveal_score_seed42_scores_full_attribution_match():
    result = simulate_factory(FactoryConfig(seed=42, units=900), "tool_calibration_drift")
    card = score_revealed_diagnosis(
        result.records, result.activation_unit, result.scenario_code, result.ground_truth
    )
    assert card["grade"] == "FULL_ATTRIBUTION_MATCH"
    assert card["score"] == 100.0
    assert all(card["checks"].values())
    assert card["blind_prediction"]["target"] == "M2"
    assert card["causal_firewall"]["truth_used_by_blind_investigator"] is False


def test_all_six_scenarios_score_full_attribution_for_reference_seed():
    scenarios = [
        "tool_calibration_drift",
        "fixture_wear_temp",
        "supplier_resin_shift",
        "gage_measurement_drift",
        "calibration_microstops",
        "changeover_deterioration",
    ]
    for scenario in scenarios:
        result = simulate_factory(FactoryConfig(seed=42, units=900), scenario)
        card = score_revealed_diagnosis(
            result.records, result.activation_unit, result.scenario_code, result.ground_truth
        )
        assert card["score"] == 100.0, (scenario, card)


def test_arena_api_overview_does_not_reveal_truth():
    created = client.post("/api/runs", json={"seed": 42, "units": 700, "scenario": "tool_calibration_drift"}).json()
    run_id = created["run_id"]
    r = client.get(f"/api/runs/{run_id}/arena/overview")
    assert r.status_code == 200
    body = r.json()
    assert body["truth_revealed"] is False
    assert body["arena"]["prediction_snapshot"]["target"] == "M2"
    assert client.get(f"/api/runs/{run_id}/ground-truth").status_code == 403


def test_arena_reveal_score_is_explicit_and_then_truth_is_available():
    created = client.post("/api/runs", json={"seed": 42, "units": 700, "scenario": "tool_calibration_drift"}).json()
    run_id = created["run_id"]
    before = client.get(f"/api/runs/{run_id}/investigation/overview").json()["investigation"]
    scored = client.post(f"/api/runs/{run_id}/arena/reveal-score")
    assert scored.status_code == 200
    body = scored.json()
    assert body["scorecard"]["score"] == 100.0
    assert "torque tool M2" in body["ground_truth"]["scenario"]["root_cause"]
    assert client.get(f"/api/runs/{run_id}/ground-truth").status_code == 200
    after = client.get(f"/api/runs/{run_id}/investigation/overview").json()["investigation"]
    assert before == after


def test_v05_frontend_exposes_arena_and_scorecard():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    html = (root / "static" / "index.html").read_text(encoding="utf-8")
    js = (root / "static" / "app.js").read_text(encoding="utf-8")
    assert "BREAK THE FACTORY / INVESTIGATION ARENA" in html
    assert "REVEAL SCORECARD" in html
    assert "loadArena" in js
    assert "/arena/reveal-score" in js
