from __future__ import annotations

import json
from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from kaizen_ai.engine import ask_kaizen
from kaizen_ai.models import AIExecutionResult, GroundedAIResponse, ToolTraceEntry
from kaizen_ai.provider import GeminiInteractionsProvider
from kaizen_ai.tools import EngineeringToolbox, TOOL_DECLARATIONS
from kaizen_factory.models import FactoryConfig
from kaizen_factory.simulator import simulate_factory


def _run():
    return simulate_factory(FactoryConfig(seed=42, units=700), "tool_calibration_drift")


class FakeGroundedProvider:
    name = "fake-grounded"
    model = "fixture-model"

    def run(self, *, question, toolbox, mode):
        inv = toolbox.call("get_investigation_summary", {})
        ledger = toolbox.call("get_evidence_ledger", {"hypothesis_code": inv["top_suspect"]["code"]})
        ids = [x["evidence_id"] for x in ledger["evidence"][:3]]
        return AIExecutionResult(
            response=GroundedAIResponse(
                mode=mode,
                headline="M2 is the strongest observational suspect",
                answer="The evidence favors M2, but L5 causal confirmation remains locked.",
                confidence_language="Strong observational support with low ambiguity; not causal confirmation.",
                evidence_ids=ids,
                contradictory_evidence=["Alternative hypotheses were evaluated in parallel."],
                assumptions=["The observable measurement system remains adequate."],
                unresolved_questions=["Would a controlled recalibration reproduce the expected improvement?"],
                recommended_next_actions=["Run a controlled intervention or DOE before causal confirmation."],
            ),
            tool_trace=[
                ToolTraceEntry(tool="get_investigation_summary", arguments={}, result_summary="leader=M2"),
                ToolTraceEntry(tool="get_evidence_ledger", arguments={"hypothesis_code": inv["top_suspect"]["code"]}, result_summary=f"evidence_rows={len(ids)}"),
            ],
            provider=self.name,
            model=self.model,
        )


class FakeUngroundedProvider(FakeGroundedProvider):
    def run(self, *, question, toolbox, mode):
        out = super().run(question=question, toolbox=toolbox, mode=mode)
        out.tool_trace = []
        return out


class FakeFabricatingProvider(FakeGroundedProvider):
    def run(self, *, question, toolbox, mode):
        out = super().run(question=question, toolbox=toolbox, mode=mode)
        out.response.evidence_ids = ["EVD-9999"]
        return out


def test_engineering_toolbox_never_exposes_sealed_truth_fields():
    r = _run()
    box = EngineeringToolbox(r.records, r.activation_unit, seed=r.config.seed, line_name=r.config.line_name)
    outputs = [
        box.call("get_investigation_summary"),
        box.call("get_evidence_ledger", {"hypothesis_code": "MACHINE_TORQUE_BIAS"}),
        box.call("get_quality_snapshot"),
        box.call("get_ie_snapshot"),
        box.call("get_causal_gate"),
        box.call("run_process_what_if", {"intervention_code": "TOOL_RECALIBRATION"}),
        box.call("solve_improvement_portfolio", {}),
    ]
    text = json.dumps(outputs, default=str).lower()
    for forbidden in ["tool_calibration_drift", "latent_fault_strength", "torque_actual_nm", "true_defect", '"root_cause"']:
        assert forbidden not in text


def test_ai_grounding_accepts_real_evidence_ids_and_preserves_causal_lock():
    r = _run()
    out = ask_kaizen(r.records, r.activation_unit, "Why do you suspect M2?", provider=FakeGroundedProvider(), seed=r.config.seed, line_name=r.config.line_name)
    assert out.grounded is True
    assert out.truth_dependency is False
    assert out.causal_confirmation_unlocked is False
    assert out.response.evidence_ids
    assert out.response.causal_status == "NOT_CAUSALLY_CONFIRMED"


def test_ai_rejects_answer_without_tool_grounding():
    r = _run()
    with pytest.raises(RuntimeError, match="no KAIZEN engineering tool"):
        ask_kaizen(r.records, r.activation_unit, "Why?", provider=FakeUngroundedProvider())


def test_ai_rejects_fabricated_evidence_id():
    r = _run()
    with pytest.raises(RuntimeError, match="unknown evidence IDs"):
        ask_kaizen(r.records, r.activation_unit, "Why?", provider=FakeFabricatingProvider())


def test_tool_declarations_do_not_offer_ground_truth_tool():
    names = {x["name"] for x in TOOL_DECLARATIONS}
    assert "get_ground_truth" not in names
    assert "reveal_ground_truth" not in names
    assert "get_investigation_summary" in names
    assert "get_diagnosis_evidence_packet" in names
    assert "solve_improvement_portfolio" in names


@dataclass
class FakeStep:
    type: str
    name: str = ""
    arguments: dict | None = None
    id: str = ""


class FakeInteraction:
    def __init__(self, *, id, steps=None, output_text=None):
        self.id = id
        self.steps = steps or []
        self.output_text = output_text


class FakeInteractionsAPI:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            return FakeInteraction(
                id="int-1",
                steps=[FakeStep(type="function_call", name="get_diagnosis_evidence_packet", arguments={}, id="call-1")],
            )
        payload = GroundedAIResponse(
            mode="ASK",
            headline="Evidence-grounded answer",
            answer="M2 is the leading suspect, but this is not causal proof.",
            confidence_language="Strong observational support.",
            evidence_ids=[],
            contradictory_evidence=["Alternative explanations remain observationally possible."],
            assumptions=["Current measurement data are adequate."],
            unresolved_questions=["Intervention response is not yet observed."],
            recommended_next_actions=["Run a controlled recalibration experiment."],
        ).model_dump_json()
        return FakeInteraction(id="int-2", steps=[], output_text=payload)


class FakeClient:
    def __init__(self):
        self.interactions = FakeInteractionsAPI()


def test_gemini_provider_forces_first_engineering_tool_and_returns_result():
    r = _run()
    box = EngineeringToolbox(r.records, r.activation_unit)
    client = FakeClient()
    provider = GeminiInteractionsProvider(model="gemini-test", client=client)
    out = provider.run(question="Why M2?", toolbox=box, mode="ASK")
    assert out.tool_trace[0].tool == "get_diagnosis_evidence_packet"
    first = client.interactions.calls[0]
    assert first["generation_config"]["tool_choice"]["allowed_tools"]["mode"] == "any"
    assert first["generation_config"]["tool_choice"]["allowed_tools"]["tools"] == ["get_diagnosis_evidence_packet"]
    assert "temperature" not in first["generation_config"]
    assert first["generation_config"]["thinking"]["thinking_level"] == "low"
    second = client.interactions.calls[1]
    assert second["previous_interaction_id"] == "int-1"
    assert second["input"][0]["type"] == "function_result"
    assert out.response.headline == "Evidence-grounded answer"


def test_red_team_mode_is_preserved_in_structured_response():
    r = _run()
    out = ask_kaizen(r.records, r.activation_unit, "Challenge the recommendation", mode="RED_TEAM", provider=FakeGroundedProvider())
    assert out.response.mode == "RED_TEAM"
    assert out.response.contradictory_evidence


def test_ai_status_endpoint_exposes_capability_not_secret(monkeypatch):
    from fastapi.testclient import TestClient
    import app.main as main_mod
    monkeypatch.setattr(main_mod, "ai_status", lambda: {
        "provider": "Google Gemini", "model": "gemini-test", "configured": True,
        "key_present": True, "sdk_available": True, "sdk": "google-genai", "api": "Interactions API",
        "function_calling": True, "structured_output": True, "ground_truth_dependency": False,
        "causal_confirmation_unlocked": False, "key_policy": "secret stays local",
    })
    body = TestClient(main_mod.app).get("/api/ai/status").json()
    text = json.dumps(body)
    assert body["ai"]["configured"] is True
    assert "api_key" not in text.lower()
    assert "secret stays local" in text


def test_ai_api_rejects_unconfigured_runtime_without_exposing_truth(monkeypatch):
    from fastapi.testclient import TestClient
    import app.main as main_mod
    monkeypatch.setattr(main_mod, "ai_status", lambda: {
        "provider": "Google Gemini", "model": "gemini-test", "configured": False,
        "key_present": False, "sdk_available": True, "sdk": "google-genai", "api": "Interactions API",
        "function_calling": True, "structured_output": True, "ground_truth_dependency": False,
        "causal_confirmation_unlocked": False, "key_policy": "secret stays local",
    })
    client = TestClient(main_mod.app)
    created = client.post("/api/runs", json={"seed": 42, "units": 300, "scenario": "tool_calibration_drift"}).json()
    r = client.post(f"/api/runs/{created['run_id']}/ai/ask", json={"question": "Why M2?", "mode": "ASK"})
    assert r.status_code == 503
    assert "Gemini is not configured" in r.json()["detail"]
    assert "Calibration bias developing" not in r.text


def test_v08_frontend_exposes_gemini_copilot_and_red_team():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    html = (root / "static" / "index.html").read_text(encoding="utf-8")
    js = (root / "static" / "app.js").read_text(encoding="utf-8")
    assert "AI / GEMINI ENGINEERING COPILOT" in html
    assert "ASK KAIZEN" in html
    assert "RED TEAM MY RECOMMENDATION" in html
    assert "FUNCTION-CALL TRACE" in html
    assert "/api/ai/status" in js
    assert "/ai/ask" in js


def test_optimizer_tool_treats_null_optional_arguments_as_defaults():
    r = _run()
    box = EngineeringToolbox(r.records, r.activation_unit, seed=r.config.seed, line_name=r.config.line_name)
    out = box.call("solve_improvement_portfolio", {
        "budget_usd": 900,
        "max_downtime_hours": 8,
        "min_good_throughput_uph": None,
        "max_defect_rate_pct": None,
        "annual_volume_units": None,
        "effectiveness": None,
        "demand_multiplier": None,
        "min_evidence_score": None,
    })
    assert out["constraints"]["budget_usd"] == 900.0
    assert out["constraints"]["max_downtime_hours"] == 8.0
    assert out["constraints"]["min_good_throughput_uph"] == 80.0
    assert out["constraints"]["annual_volume_units"] == 200000
    assert out["solver"]["status"] == "INFEASIBLE"


def test_what_if_tool_treats_null_optional_arguments_as_defaults():
    r = _run()
    box = EngineeringToolbox(r.records, r.activation_unit, seed=r.config.seed, line_name=r.config.line_name)
    out = box.call("run_process_what_if", {
        "intervention_code": "TOOL_RECALIBRATION",
        "effectiveness": None,
        "demand_multiplier": None,
    })
    assert out["settings"]["effectiveness"] == 1.0
    assert out["settings"]["demand_multiplier"] == 1.0


def test_ai_api_never_exposes_opaque_500_for_unexpected_ai_exception(monkeypatch):
    from fastapi.testclient import TestClient
    import app.main as main_mod
    monkeypatch.setattr(main_mod, "ai_status", lambda: {
        "provider": "Google Gemini", "model": "gemini-test", "configured": True,
        "key_present": True, "sdk_available": True, "sdk": "google-genai", "api": "Interactions API",
        "function_calling": True, "structured_output": True, "ground_truth_dependency": False,
        "causal_confirmation_unlocked": False, "key_policy": "secret stays local",
    })
    monkeypatch.setattr(main_mod, "ask_kaizen", lambda *a, **k: (_ for _ in ()).throw(TypeError("optional tool argument was null")))
    client = TestClient(main_mod.app)
    created = client.post("/api/runs", json={"seed": 42, "units": 300, "scenario": "tool_calibration_drift"}).json()
    resp = client.post(f"/api/runs/{created['run_id']}/ai/ask", json={"question": "Budget 900", "mode": "ASK"})
    assert resp.status_code == 502
    assert "TypeError" in resp.json()["detail"]
    assert resp.status_code != 500


class FakeNullOptimizerInteractionsAPI:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        n = len(self.calls)
        if n == 1:
            return FakeInteraction(
                id="int-n1",
                steps=[FakeStep(type="function_call", name="get_investigation_summary", arguments={}, id="call-n1")],
            )
        if n == 2:
            return FakeInteraction(
                id="int-n2",
                steps=[FakeStep(type="function_call", name="solve_improvement_portfolio", arguments={
                    "budget_usd": 900,
                    "max_downtime_hours": 8,
                    "min_good_throughput_uph": None,
                    "max_defect_rate_pct": None,
                    "annual_volume_units": None,
                    "effectiveness": None,
                    "demand_multiplier": None,
                    "min_evidence_score": None,
                }, id="call-n2")],
            )
        payload = GroundedAIResponse(
            mode="ASK",
            headline="The $900 budget cannot meet the throughput floor",
            answer="The exact optimizer found no feasible portfolio under the stated budget and the default 80 good units/hour requirement.",
            confidence_language="Exact result within the modeled intervention catalog and constraints; not causal proof.",
            evidence_ids=[],
            contradictory_evidence=["No-action remains below the throughput floor."],
            assumptions=["Unspecified optimizer fields use KAIZEN defaults."],
            unresolved_questions=["Could the throughput requirement be relaxed?"],
            recommended_next_actions=["Increase budget or relax the throughput constraint."],
        ).model_dump_json()
        return FakeInteraction(id="int-n3", steps=[], output_text=payload)


class FakeNullOptimizerClient:
    def __init__(self):
        self.interactions = FakeNullOptimizerInteractionsAPI()


def test_gemini_provider_budget_path_survives_null_optional_tool_arguments():
    r = _run()
    box = EngineeringToolbox(r.records, r.activation_unit)
    provider = GeminiInteractionsProvider(model="gemini-test", client=FakeNullOptimizerClient())
    out = provider.run(question="I have a $900 budget and 8 hours downtime. What should I do?", toolbox=box, mode="ASK")
    assert any(t.tool == "solve_improvement_portfolio" for t in out.tool_trace)
    assert out.response.headline.startswith("The $900 budget")
    second_result = provider.client.interactions.calls[2]["input"] if len(provider.client.interactions.calls) > 2 else None
    assert out.causal_confirmation_unlocked is False

class FakeRateLimitError(Exception):
    status_code = 429


class FakeQuotaFallbackInteractionsAPI:
    def __init__(self):
        self.calls = []
        self.success_count = 0

    def create(self, **kwargs):
        self.calls.append(kwargs)
        model = kwargs.get("model")
        if model == "gemini-3.6-flash":
            raise FakeRateLimitError("Quota exceeded for metric generate_content_free_tier_requests")
        self.success_count += 1
        if self.success_count == 1:
            return FakeInteraction(
                id="fallback-int-1",
                steps=[FakeStep(type="function_call", name="get_investigation_summary", arguments={}, id="fallback-call-1")],
            )
        payload = GroundedAIResponse(
            mode="ASK",
            headline="Flash-Lite grounded answer",
            answer="M2 remains the leading observational suspect after quota fallback.",
            confidence_language="Strong observational support; not causal proof.",
            evidence_ids=[],
            contradictory_evidence=["Competing explanations remain observationally possible."],
            assumptions=["The fallback model receives the same KAIZEN tool contract."],
            unresolved_questions=["Controlled intervention evidence is still absent."],
            recommended_next_actions=["Run a controlled intervention before causal confirmation."],
        ).model_dump_json()
        return FakeInteraction(id="fallback-int-2", steps=[], output_text=payload)


class FakeQuotaFallbackClient:
    def __init__(self):
        self.interactions = FakeQuotaFallbackInteractionsAPI()


def test_gemini_provider_falls_back_from_quota_exhausted_model_and_records_actual_model():
    r = _run()
    box = EngineeringToolbox(r.records, r.activation_unit)
    client = FakeQuotaFallbackClient()
    provider = GeminiInteractionsProvider(
        model="gemini-3.6-flash",
        fallback_models=["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"],
        client=client,
    )
    out = provider.run(question="Why M2?", toolbox=box, mode="ASK")
    attempted_models = [call["model"] for call in client.interactions.calls]
    assert attempted_models[0] == "gemini-3.6-flash"
    assert attempted_models[1] == "gemini-3.5-flash-lite"
    assert attempted_models[-1] == "gemini-3.5-flash-lite"
    assert out.model == "gemini-3.5-flash-lite"
    assert out.tool_trace[0].tool == "get_investigation_summary"


def test_v082_default_model_is_flash_lite_and_status_exposes_fallback_chain():
    import kaizen_ai.provider as provider_mod
    assert provider_mod.DEFAULT_MODEL == "gemini-3.5-flash-lite"
    status = provider_mod.ai_status()
    assert status["model"] == "gemini-3.5-flash-lite"
    assert status["quota_fallback"] is True
    assert "gemini-3.1-flash-lite" in status["model_chain"]
    assert "gemini-2.5-flash-lite" in status["model_chain"]

class FakeMisfiledEngineeringReferenceProvider(FakeGroundedProvider):
    """Reproduce Flash-Lite placing hypothesis/intervention codes in evidence_ids."""
    def run(self, *, question, toolbox, mode):
        inv = toolbox.call("get_investigation_summary", {})
        ledger = toolbox.call("get_evidence_ledger", {"hypothesis_code": inv["top_suspect"]["code"]})
        real_id = ledger["evidence"][0]["evidence_id"]
        solved = toolbox.call("solve_improvement_portfolio", {
            "budget_usd": 900,
            "max_downtime_hours": 8,
            "min_good_throughput_uph": 80,
            "annual_volume_units": None,
            "effectiveness": None,
            "demand_multiplier": None,
            "min_evidence_score": None,
        })
        return AIExecutionResult(
            response=GroundedAIResponse(
                mode=mode,
                headline="Budget is insufficient for the leading action",
                answer="The $900 budget cannot fund the M2 torque-tool recalibration while preserving the 80 good units/hour requirement.",
                confidence_language="Grounded in the current statistical diagnosis and exact portfolio optimizer.",
                # This deliberately reproduces the V0.8.3 live-model field confusion.
                evidence_ids=[real_id, "MACHINE_TORQUE_BIAS", "GAGE_MEASUREMENT_DRIFT", "GAGE_RECALIBRATION"],
                contradictory_evidence=["Measurement drift remains a lower-ranked competing explanation."],
                assumptions=["The optimizer defaults apply to omitted optional parameters."],
                unresolved_questions=["Would management accept a lower throughput requirement?"],
                recommended_next_actions=["Increase budget above the modeled recalibration cost or relax a hard constraint."],
            ),
            tool_trace=[
                ToolTraceEntry(tool="get_investigation_summary", arguments={}, result_summary="leader=M2"),
                ToolTraceEntry(tool="get_evidence_ledger", arguments={"hypothesis_code": inv["top_suspect"]["code"]}, result_summary=f"evidence_rows={ledger['count']}"),
                ToolTraceEntry(tool="solve_improvement_portfolio", arguments={"budget_usd": 900, "max_downtime_hours": 8, "min_good_throughput_uph": 80}, result_summary=f"optimizer={solved['solver']['status']}"),
            ],
            provider="fake-flash-lite",
            model="gemini-3.5-flash-lite",
        )


class FakeUnknownEngineeringReferenceProvider(FakeGroundedProvider):
    def run(self, *, question, toolbox, mode):
        out = super().run(question=question, toolbox=toolbox, mode=mode)
        out.response.evidence_ids = ["TOTALLY_FAKE_ENGINEERING_CODE"]
        return out


def test_ai_normalizes_recognized_engineering_codes_misfiled_as_evidence_ids():
    r = _run()
    out = ask_kaizen(
        r.records, r.activation_unit,
        "I have a $900 budget, maximum 8 hours downtime, and need at least 80 good units per hour. What should I do?",
        provider=FakeMisfiledEngineeringReferenceProvider(), seed=r.config.seed, line_name=r.config.line_name,
    )
    assert out.response.evidence_ids and all(x.startswith("EVD-") for x in out.response.evidence_ids)
    assert "MACHINE_TORQUE_BIAS" in out.response.engineering_references
    assert "GAGE_MEASUREMENT_DRIFT" in out.response.engineering_references
    assert "GAGE_RECALIBRATION" in out.response.engineering_references
    assert any(t.tool == "solve_improvement_portfolio" for t in out.tool_trace)


def test_ai_still_rejects_unknown_non_evidence_reference_tokens():
    r = _run()
    with pytest.raises(RuntimeError, match="unknown engineering references"):
        ask_kaizen(r.records, r.activation_unit, "Why?", provider=FakeUnknownEngineeringReferenceProvider())

class FakeOptimizerLoopInteractionsAPI:
    """Reproduce Flash-Lite asking the optimizer repeatedly instead of synthesizing."""
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        n = len(self.calls)
        if n == 1:
            return FakeInteraction(
                id="loop-int-1",
                steps=[FakeStep(type="function_call", name="get_investigation_summary", arguments={}, id="loop-call-1")],
            )
        if n == 2:
            return FakeInteraction(
                id="loop-int-2",
                steps=[FakeStep(type="function_call", name="solve_improvement_portfolio", arguments={
                    "budget_usd": 900,
                    "max_downtime_hours": 8,
                    "min_good_throughput_uph": 80,
                }, id="loop-call-2")],
            )
        # If KAIZEN mistakenly keeps tools open, imitate the live looping behavior.
        if "tools" in kwargs:
            return FakeInteraction(
                id=f"loop-int-{n}",
                steps=[FakeStep(type="function_call", name="solve_improvement_portfolio", arguments={
                    "budget_usd": 900,
                    "max_downtime_hours": 8,
                    "min_good_throughput_uph": 80,
                }, id=f"loop-call-{n}")],
            )
        payload = GroundedAIResponse(
            mode="ASK",
            headline="The $900 constraint set is infeasible",
            answer="The exact portfolio optimizer found no feasible intervention under the $900 budget while maintaining at least 80 good units/hour.",
            confidence_language="Exact within KAIZEN's modeled catalog and constraints; not causal proof.",
            evidence_ids=[],
            engineering_references=["TOOL_RECALIBRATION"],
            contradictory_evidence=["No-action remains below the 80 good units/hour requirement."],
            assumptions=["Unspecified optimizer settings use KAIZEN defaults."],
            unresolved_questions=["Could the budget or throughput floor be relaxed?"],
            recommended_next_actions=["Increase budget to fund the leading intervention or relax a hard constraint."],
        ).model_dump_json()
        return FakeInteraction(id="loop-final", steps=[], output_text=payload)


class FakeOptimizerLoopClient:
    def __init__(self):
        self.interactions = FakeOptimizerLoopInteractionsAPI()


def test_gemini_optimizer_result_closes_tool_phase_and_forces_final_synthesis():
    r = _run()
    box = EngineeringToolbox(r.records, r.activation_unit)
    client = FakeOptimizerLoopClient()
    provider = GeminiInteractionsProvider(model="gemini-test", client=client)
    out = provider.run(
        question="I have a $900 budget, maximum 8 hours downtime, and need at least 80 good units per hour. What should I do?",
        toolbox=box,
        mode="ASK",
    )
    assert out.response.headline == "The $900 constraint set is infeasible"
    assert [t.tool for t in out.tool_trace] == ["get_investigation_summary", "solve_improvement_portfolio"]
    assert len(client.interactions.calls) == 3
    final_call = client.interactions.calls[-1]
    assert "tools" not in final_call
    assert final_call["previous_interaction_id"] == "loop-int-2"
    assert "FINAL SYNTHESIS PHASE" in final_call["system_instruction"]


class FakeDuplicateToolLoopInteractionsAPI:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        n = len(self.calls)
        if n == 1:
            return FakeInteraction(
                id="dup-int-1",
                steps=[FakeStep(type="function_call", name="get_investigation_summary", arguments={}, id="dup-call-1")],
            )
        if n in {2, 3}:
            return FakeInteraction(
                id=f"dup-int-{n}",
                steps=[FakeStep(type="function_call", name="get_evidence_ledger", arguments={"hypothesis_code": "MACHINE_TORQUE_BIAS"}, id=f"dup-call-{n}")],
            )
        if "tools" in kwargs:
            raise AssertionError("KAIZEN should close tools after a duplicate-only round")
        payload = GroundedAIResponse(
            mode="ASK",
            headline="Duplicate evidence request was bounded",
            answer="The existing M2 evidence is sufficient for an observational explanation; no additional repeated ledger fetch is needed.",
            confidence_language="Grounded observational synthesis.",
            evidence_ids=[],
            engineering_references=["MACHINE_TORQUE_BIAS"],
            contradictory_evidence=[],
            assumptions=[],
            unresolved_questions=["Intervention confirmation remains absent."],
            recommended_next_actions=["Use controlled intervention evidence for causal confirmation."],
        ).model_dump_json()
        return FakeInteraction(id="dup-final", steps=[], output_text=payload)


class FakeDuplicateToolLoopClient:
    def __init__(self):
        self.interactions = FakeDuplicateToolLoopInteractionsAPI()


def test_repeated_identical_tool_call_is_cached_and_forces_final_synthesis():
    r = _run()
    box = EngineeringToolbox(r.records, r.activation_unit)
    client = FakeDuplicateToolLoopClient()
    provider = GeminiInteractionsProvider(model="gemini-test", client=client)
    out = provider.run(question="Why M2?", toolbox=box, mode="ASK")
    assert out.response.headline == "Duplicate evidence request was bounded"
    assert len(client.interactions.calls) == 4
    assert "tools" not in client.interactions.calls[-1]
    evidence_traces = [t for t in out.tool_trace if t.tool == "get_evidence_ledger"]
    assert len(evidence_traces) == 2
    assert evidence_traces[-1].result_summary.startswith("cached-repeat;")

class FakeRuntimeEntityReferenceProvider(FakeGroundedProvider):
    """Reproduce live Flash-Lite returning asset IDs as engineering references."""
    def run(self, *, question, toolbox, mode):
        out = super().run(question=question, toolbox=toolbox, mode=mode)
        out.response.engineering_references = [
            "M2", "G1", "F4", "S1", "S1-L103", "O3", "A", "Calibration",
            "MACHINE_TORQUE_BIAS", "TOOL_RECALIBRATION",
        ]
        return out


class FakeRuntimeEntityMisfiledProvider(FakeGroundedProvider):
    """Runtime entities may be misplaced into evidence_ids by a smaller model."""
    def run(self, *, question, toolbox, mode):
        out = super().run(question=question, toolbox=toolbox, mode=mode)
        real_evd = out.response.evidence_ids[0]
        out.response.evidence_ids = [real_evd, "G1", "M2"]
        out.response.engineering_references = ["f4", "calibration"]  # casing normalization too
        return out


class FakeInventedRuntimeAssetProvider(FakeGroundedProvider):
    def run(self, *, question, toolbox, mode):
        out = super().run(question=question, toolbox=toolbox, mode=mode)
        out.response.engineering_references = ["M99"]
        return out


def test_ai_accepts_observable_runtime_assets_as_engineering_references():
    r = _run()
    out = ask_kaizen(
        r.records,
        r.activation_unit,
        "Explain the current run references",
        provider=FakeRuntimeEntityReferenceProvider(),
        seed=r.config.seed,
        line_name=r.config.line_name,
    )
    refs = set(out.response.engineering_references)
    for expected in {"M2", "G1", "F4", "S1", "S1-L103", "O3", "A", "Calibration", "MACHINE_TORQUE_BIAS", "TOOL_RECALIBRATION"}:
        assert expected in refs


def test_ai_normalizes_runtime_assets_misfiled_as_evidence_ids_and_casing():
    r = _run()
    out = ask_kaizen(
        r.records,
        r.activation_unit,
        "Why M2 and what about G1?",
        provider=FakeRuntimeEntityMisfiledProvider(),
        seed=r.config.seed,
        line_name=r.config.line_name,
    )
    assert all(x.startswith("EVD-") for x in out.response.evidence_ids)
    refs = set(out.response.engineering_references)
    assert {"M2", "G1", "F4", "Calibration"}.issubset(refs)


def test_ai_rejects_invented_runtime_asset_reference():
    r = _run()
    with pytest.raises(RuntimeError, match="unknown engineering references"):
        ask_kaizen(
            r.records,
            r.activation_unit,
            "Is M99 involved?",
            provider=FakeInventedRuntimeAssetProvider(),
            seed=r.config.seed,
            line_name=r.config.line_name,
        )


def test_ai_accepts_every_current_investigator_target_as_reference():
    r = _run()
    box = EngineeringToolbox(r.records, r.activation_unit, seed=r.config.seed, line_name=r.config.line_name)
    inv = box.call("get_investigation_summary")

    class TargetProvider(FakeGroundedProvider):
        def run(self, *, question, toolbox, mode):
            out = super().run(question=question, toolbox=toolbox, mode=mode)
            out.response.engineering_references = [h["target"] for h in inv["ranked_hypotheses"]]
            return out

    out = ask_kaizen(
        r.records,
        r.activation_unit,
        "List the challenged targets",
        provider=TargetProvider(),
        seed=r.config.seed,
        line_name=r.config.line_name,
    )
    assert set(out.response.engineering_references) == {h["target"] for h in inv["ranked_hypotheses"]}


class FakeWrongOptimizerNarrativeProvider:
    name = "fake-wrong-optimizer"
    model = "fixture-model"

    def run(self, *, question, toolbox, mode):
        solved = toolbox.call("solve_improvement_portfolio", {
            "budget_usd": 900,
            "max_downtime_hours": 8,
            "min_good_throughput_uph": 80,
        })
        return AIExecutionResult(
            response=GroundedAIResponse(
                mode=mode,
                headline="Recalibrate M2 within budget",
                answer="TOOL_RECALIBRATION satisfies the $900 budget and should be implemented.",
                confidence_language="High confidence.",
                evidence_ids=[],
                engineering_references=["TOOL_RECALIBRATION", "M2"],
                contradictory_evidence=[],
                assumptions=[],
                unresolved_questions=[],
                recommended_next_actions=["Recalibrate M2."],
            ),
            tool_trace=[ToolTraceEntry(
                tool="solve_improvement_portfolio",
                arguments={"budget_usd": 900, "max_downtime_hours": 8, "min_good_throughput_uph": 80},
                result_summary=f"optimizer={solved['solver']['status']}",
            )],
            provider=self.name,
            model=self.model,
        )


def test_optimizer_semantic_guard_overrides_llm_prose_that_contradicts_hard_constraints():
    r = _run()
    out = ask_kaizen(
        r.records, r.activation_unit,
        "I have a $900 budget, maximum 8 hours downtime, and need at least 80 good units per hour. What should I do?",
        provider=FakeWrongOptimizerNarrativeProvider(), seed=r.config.seed, line_name=r.config.line_name,
    )
    assert "No feasible" in out.response.headline
    assert "INFEASIBLE" in out.response.answer
    assert "$900" in out.response.answer
    assert "nearest evaluated portfolio" in out.response.answer
    assert out.response.recommended_next_actions == ["Relax at least one hard constraint or expand the intervention/resource catalog, then rerun the exact optimizer."]
    assert "satisfies the $900 budget" not in out.response.answer


class FakeSparseEvidenceProvider:
    name = "fake-sparse-evidence"
    model = "fixture-model"

    def run(self, *, question, toolbox, mode):
        inv = toolbox.call("get_investigation_summary", {})
        return AIExecutionResult(
            response=GroundedAIResponse(
                mode=mode,
                headline="M2 remains strongest",
                answer="M2 has the strongest observational signal.",
                confidence_language="Strong observational support.",
                evidence_ids=[],
                engineering_references=["M2"],
                contradictory_evidence=[],
                assumptions=[],
                unresolved_questions=["Controlled intervention remains absent."],
                recommended_next_actions=["Test M2."],
            ),
            tool_trace=[ToolTraceEntry(tool="get_investigation_summary", arguments={}, result_summary=f"leader={inv['top_suspect']['target']}")],
            provider=self.name, model=self.model,
        )


def test_evidence_question_is_backfilled_with_real_ledger_ids_and_known_limitations():
    r = _run()
    out = ask_kaizen(
        r.records, r.activation_unit,
        "Why do you suspect M2? Give me the strongest evidence and what still argues against it.",
        provider=FakeSparseEvidenceProvider(), seed=r.config.seed, line_name=r.config.line_name,
    )
    assert out.response.evidence_ids[:3] == ["EVD-0001", "EVD-0002", "EVD-0003"]
    assert any("product mix" in x.lower() for x in out.response.contradictory_evidence)
    assert out.response.assumptions


def test_red_team_never_renders_empty_contradictory_evidence_when_investigator_has_confounders():
    r = _run()
    out = ask_kaizen(
        r.records, r.activation_unit,
        "Challenge M2", mode="RED_TEAM",
        provider=FakeSparseEvidenceProvider(), seed=r.config.seed, line_name=r.config.line_name,
    )
    assert out.response.evidence_ids
    assert len(out.response.contradictory_evidence) >= 2
    assert any("Potential confounder" in x for x in out.response.contradictory_evidence)
