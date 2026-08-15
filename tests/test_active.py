from fastapi.testclient import TestClient

from app.main import app
from kaizen_active import (
    build_active_investigation_overview,
    build_experiment_design,
    execute_controlled_experiment,
    execute_observational_probe,
    freeze_human_prediction,
    score_human_prediction,
)
from kaizen_factory.models import FactoryConfig
from kaizen_factory.scenarios import FAULT_CATALOG
from kaizen_factory.simulator import simulate_factory


def test_i_dont_know_mode_exists_on_a_deliberately_small_blind_sample():
    run = simulate_factory(FactoryConfig(seed=0, units=100), "random")
    active = build_active_investigation_overview(run.records, run.activation_unit)
    assert active["uncertainty"]["state"] == "I_DONT_KNOW"
    assert "does not separate" in active["uncertainty"]["rationale"].lower()


def test_value_of_information_prefers_a_current_decision_relevant_probe():
    run = simulate_factory(FactoryConfig(seed=42, units=700), "tool_calibration_drift")
    active = build_active_investigation_overview(run.records, run.activation_unit)
    best = active["value_of_information"]["recommended_next_measurement"]
    assert best["hypothesis_code"] in {
        active["active_investigation"]["leading_hypothesis"]["code"],
        active["value_of_information"]["ranked_candidates"][1]["hypothesis_code"],
    }
    assert best["formal_expected_value"] is False


def test_active_probe_adds_observational_evidence_but_never_unlocks_causality():
    run = simulate_factory(FactoryConfig(seed=42, units=700), "tool_calibration_drift")
    active = build_active_investigation_overview(run.records, run.activation_unit)
    code = active["value_of_information"]["recommended_next_measurement"]["code"]
    probe = execute_observational_probe(run.records, run.activation_unit, code)
    assert probe["causal_confirmation_unlocked"] is False
    assert 0 <= probe["result"]["p_value"] <= 1
    assert probe["belief_update"]["ranking"]


def test_predeclared_controlled_experiment_confirms_all_six_correct_benchmark_mechanisms():
    for scenario in FAULT_CATALOG:
        run = simulate_factory(FactoryConfig(seed=42, units=700), scenario)
        design = build_experiment_design(run.records, run.activation_unit)
        outcome = execute_controlled_experiment(
            run.records, run.activation_unit, run.scenario_code, design["experiment_code"], seed=42
        )
        assert outcome["causal_confirmation"]["passed"] is True, (scenario, outcome)
        assert outcome["truth_boundary"]["scenario_code_exposed_in_output"] is False
        assert outcome["truth_boundary"]["ground_truth_exposed_in_output"] is False


def test_wrong_controlled_experiment_fails_and_requires_belief_revision():
    run = simulate_factory(FactoryConfig(seed=42, units=700), "tool_calibration_drift")
    outcome = execute_controlled_experiment(
        run.records, run.activation_unit, run.scenario_code, "DOE_GAGE_RECALIBRATION", seed=42
    )
    assert outcome["causal_confirmation"]["passed"] is False
    assert outcome["belief_revision"]["outcome"] == "FAILED_CONFIRMATION"
    assert outcome["belief_revision"]["next_leader_if_failed"] is not None


def test_human_prediction_is_scored_against_hidden_truth_only_after_freeze():
    run = simulate_factory(FactoryConfig(seed=42, units=700), "tool_calibration_drift")
    pred = freeze_human_prediction(run.records, run.activation_unit, "MACHINE_TORQUE_BIAS")
    score = score_human_prediction(pred, run.scenario_code)
    assert score["score"] == 100.0
    assert score["dimensions_correct"] == 4


def test_v09_api_active_human_and_experiment_flow():
    client = TestClient(app)
    created = client.post("/api/runs", json={"seed": 42, "units": 700, "scenario": "tool_calibration_drift"})
    assert created.status_code == 201
    run_id = created.json()["run_id"]

    active = client.get(f"/api/runs/{run_id}/active/overview")
    assert active.status_code == 200
    assert active.json()["active"]["causal_confirmation"]["level_5"] == "LOCKED"

    choices = client.get(f"/api/runs/{run_id}/human-vs-ai").json()["human_vs_ai"]["available_choices"]
    assert len(choices) == 6
    frozen = client.post(f"/api/runs/{run_id}/human-vs-ai/predict", json={"hypothesis_code": "MACHINE_TORQUE_BIAS"})
    assert frozen.status_code == 200
    assert frozen.json()["human_prediction"]["frozen"] is True

    design = client.get(f"/api/runs/{run_id}/experiment/design").json()["design"]
    blocked = client.post(f"/api/runs/{run_id}/experiment/execute", json={"experiment_code": design["experiment_code"], "authorized": False})
    assert blocked.status_code == 403
    executed = client.post(f"/api/runs/{run_id}/experiment/execute", json={"experiment_code": design["experiment_code"], "authorized": True})
    assert executed.status_code == 200
    assert executed.json()["experiment"]["causal_confirmation"]["passed"] is True
    assert executed.json()["ground_truth_returned"] is False

    reveal = client.post(f"/api/runs/{run_id}/arena/reveal-score")
    assert reveal.status_code == 200
    status = client.get(f"/api/runs/{run_id}/human-vs-ai").json()["human_vs_ai"]
    assert status["human_score"]["score"] == 100.0
    assert status["ai_score"]["score"] == 100.0


def test_human_prediction_cannot_be_changed_after_reveal():
    client = TestClient(app)
    created = client.post("/api/runs", json={"seed": 42, "units": 500, "scenario": "tool_calibration_drift"})
    run_id = created.json()["run_id"]
    client.post(f"/api/runs/{run_id}/arena/reveal-score")
    response = client.post(f"/api/runs/{run_id}/human-vs-ai/predict", json={"hypothesis_code": "MACHINE_TORQUE_BIAS"})
    assert response.status_code == 409


def test_gemini_toolbox_exposes_active_plan_and_experiment_design_without_truth():
    from kaizen_ai.tools import EngineeringToolbox
    run = simulate_factory(FactoryConfig(seed=42, units=700), "tool_calibration_drift")
    box = EngineeringToolbox(run.records, run.activation_unit)
    active = box.call("get_active_investigation_plan", {})
    design = box.call("get_experiment_design", {})
    assert active["uncertainty"]["state"] == "STRONG_SUSPECT"
    assert design["experiment_code"] == "DOE_TOOL_RECALIBRATION"
    assert "scenario_code" not in str(active).lower()
    assert "ground_truth" not in str(design).lower()


def test_ai_reference_validator_accepts_v09_probe_and_experiment_codes():
    from kaizen_ai.engine import ask_kaizen
    from kaizen_ai.models import AIExecutionResult, GroundedAIResponse, ToolTraceEntry

    class V09FixtureProvider:
        name = "v09-reference-fixture"
        model = "offline"
        def run(self, *, question, toolbox, mode):
            design = toolbox.call("get_experiment_design", {})
            active = toolbox.call("get_active_investigation_plan", {})
            return AIExecutionResult(
                response=GroundedAIResponse(
                    mode=mode,
                    headline="V0.9 plan",
                    answer="Use the ranked observational probe, then run only an explicitly authorized DOE.",
                    confidence_language="Planning only; no causal execution occurred.",
                    evidence_ids=[],
                    engineering_references=[
                        design["experiment_code"],
                        active["value_of_information"]["recommended_next_measurement"]["code"],
                    ],
                    contradictory_evidence=[], assumptions=[], unresolved_questions=[], recommended_next_actions=[],
                ),
                tool_trace=[ToolTraceEntry(tool="get_active_investigation_plan", arguments={}, result_summary="active plan")],
                provider=self.name, model=self.model,
            )

    run = simulate_factory(FactoryConfig(seed=42, units=700), "tool_calibration_drift")
    out = ask_kaizen(run.records, run.activation_unit, "What should we measure next?", provider=V09FixtureProvider())
    assert "DOE_TOOL_RECALIBRATION" in out.response.engineering_references
    assert "PRODUCT_BALANCED_MACHINE_CHECK" in out.response.engineering_references


def test_v091_new_run_resets_stale_experiment_belief_copy():
    from pathlib import Path
    js = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text(encoding="utf-8")
    reset_start = js.index("function resetTruthForNewRun()")
    reset_end = js.index("async function breakFactory()", reset_start)
    reset_block = js[reset_start:reset_end]
    assert "beliefRevision" in reset_block
    assert "later satisfies every confirmation criterion" in reset_block
    assert "No controlled experiment executed." in reset_block


def test_v091_active_overview_defensively_renders_pre_doe_state_when_no_experiment_result():
    from pathlib import Path
    js = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text(encoding="utf-8")
    render_start = js.index("function renderActiveOverview(a)")
    render_end = js.index("async function loadHumanVsAI()", render_start)
    block = js[render_start:render_end]
    assert "if (a.experiment_result)" in block
    assert "No controlled experiment executed." in block
    assert "later satisfies every confirmation criterion" in block
