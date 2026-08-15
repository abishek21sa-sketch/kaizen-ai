from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def check(name: str, fn) -> bool:
    try:
        detail = fn()
        print(f"[PASS] {name}: {detail}")
        return True
    except Exception as exc:
        print(f"[FAIL] {name}: {type(exc).__name__}: {exc}")
        return False


def main() -> int:
    results = []
    results.append(check("Python", lambda: sys.version.split()[0]))
    results.append(check("FastAPI import", lambda: importlib.import_module("fastapi").__version__))
    results.append(check("Uvicorn import", lambda: importlib.import_module("uvicorn").__version__))

    def simulator_check():
        from kaizen_factory.models import FactoryConfig
        from kaizen_factory.simulator import simulate_factory
        r = simulate_factory(FactoryConfig(seed=31415, units=400), "gage_measurement_drift")
        forbidden = {"torque_actual_nm", "true_defect", "measurement_bias_nm"}
        leaked = forbidden & set(r.records[0])
        if leaked:
            raise RuntimeError(f"causal firewall leak: {sorted(leaked)}")
        if len(r.records) != 400:
            raise RuntimeError("wrong record count")
        return f"{len(r.records)} records; causal firewall intact"

    def quality_check():
        from kaizen_factory.models import FactoryConfig
        from kaizen_factory.simulator import simulate_factory
        from kaizen_quality import build_quality_overview
        r = simulate_factory(FactoryConfig(seed=2718, units=500), "tool_calibration_drift")
        q = build_quality_overview(r.records, r.activation_unit, line_name=r.config.line_name, seed=r.config.seed)
        if q["data_quality"]["status"] != "PASS":
            raise RuntimeError("observable data-quality gate failed")
        if q["evidence_state"]["ground_truth_dependency"] is not False:
            raise RuntimeError("quality engine declared a ground-truth dependency")
        return f"capability={len(q['capability']['analyses'])} analyses; SPC/MSA/COPQ ready"

    results.append(check("Hidden factory", simulator_check))
    results.append(check("Lean Six Sigma engine", quality_check))

    def ie_check():
        from kaizen_factory.models import FactoryConfig
        from kaizen_factory.simulator import simulate_factory
        from kaizen_ie import build_ie_overview
        r = simulate_factory(FactoryConfig(seed=1618, units=700), "changeover_deterioration")
        ie = build_ie_overview(r.records, r.activation_unit)
        if ie["evidence_state"]["ground_truth_dependency"] is not False:
            raise RuntimeError("IE engine declared a ground-truth dependency")
        if ie["flow"]["post"]["little_law_error_pct"] > 1e-6:
            raise RuntimeError("Little's Law reference closure failed")
        if ie["queueing"]["post"]["little_law_cell_error_pct"] > 1e-6:
            raise RuntimeError("queueing Little's Law closure failed")
        return f"takt={ie['takt']['takt_seconds_per_unit']:.1f}s; bottleneck={ie['capacity']['post']['bottleneck']['station']}; queue/WIP ready"
    results.append(check("Industrial Engineering engine", ie_check))

    def investigator_check():
        from kaizen_factory.models import FactoryConfig
        from kaizen_factory.simulator import simulate_factory
        from kaizen_investigator import build_investigation_overview
        r = simulate_factory(FactoryConfig(seed=42, units=700), "tool_calibration_drift")
        inv = build_investigation_overview(r.records, r.activation_unit)
        if inv["top_suspect"]["code"] != "MACHINE_TORQUE_BIAS":
            raise RuntimeError(f"unexpected benchmark leader: {inv['top_suspect']['code']}")
        if inv["methodology"]["latent_ground_truth_available"] is not False:
            raise RuntimeError("investigator declared latent ground-truth access")
        if inv["causality_gate"]["levels"][-1]["passed"] is not False:
            raise RuntimeError("DOE confirmation gate must remain locked")
        if inv["adjusted_models"]["models_fit"] < 4:
            raise RuntimeError("adjusted regression/ANOVA model suite incomplete")
        return f"leader={inv['top_suspect']['code']}; evidence={inv['top_suspect']['evidence_score']:.1f}; models={inv['adjusted_models']['models_fit']}/5; causal gate locked"

    results.append(check("Statistical investigator", investigator_check))

    def arena_check():
        from kaizen_arena import build_arena_overview, score_revealed_diagnosis
        from kaizen_factory.models import FactoryConfig
        from kaizen_factory.simulator import simulate_factory
        r = simulate_factory(FactoryConfig(seed=42, units=700), "tool_calibration_drift")
        arena = build_arena_overview(r.records, r.activation_unit)
        if arena["truth_available_to_investigator"] is not False:
            raise RuntimeError("arena leaked truth access before reveal")
        if arena["prediction_snapshot"]["target"] != "M2":
            raise RuntimeError("arena attribution regression failed")
        card = score_revealed_diagnosis(r.records, r.activation_unit, r.scenario_code, r.ground_truth)
        if card["score"] != 100.0:
            raise RuntimeError(f"arena reference score was {card['score']}")
        return f"timeline={len(arena['timeline'])} events; reference attribution={card['dimensions_correct']}/{card['dimensions_total']}"

    results.append(check("Investigation arena", arena_check))

    def simulation_check():
        from kaizen_factory.models import FactoryConfig
        from kaizen_factory.simulator import simulate_factory
        from kaizen_simulation import build_simulation_overview
        r = simulate_factory(FactoryConfig(seed=42, units=700), "tool_calibration_drift")
        sim = build_simulation_overview(r.records, r.activation_unit)
        if sim["evidence_state"]["ground_truth_dependency"] is not False:
            raise RuntimeError("simulation declared a ground-truth dependency")
        if sim["recommended_intervention_code"] != "TOOL_RECALIBRATION":
            raise RuntimeError(f"unexpected recommendation: {sim['recommended_intervention_code']}")
        w = sim["recommended_intervention"]
        if w["counterfactual"]["defect_rate"] >= w["baseline"]["defect_rate"]:
            raise RuntimeError("reference counterfactual did not improve defect rate")
        if w["counterfactual"]["copq_per_1000_units_usd"] >= w["baseline"]["copq_per_1000_units_usd"]:
            raise RuntimeError("reference counterfactual did not reduce COPQ")
        return f"recommended={sim['recommended_intervention_code']}; defect {w['baseline']['defect_rate']:.3f}->{w['counterfactual']['defect_rate']:.3f}; paired replay ready"

    results.append(check("Process simulation lab", simulation_check))

    def optimizer_check():
        from kaizen_factory.models import FactoryConfig
        from kaizen_factory.simulator import simulate_factory
        from kaizen_optimizer import solve_improvement_portfolio
        r = simulate_factory(FactoryConfig(seed=42, units=700), "tool_calibration_drift")
        o = solve_improvement_portfolio(r.records, r.activation_unit)
        if o["evidence_state"]["ground_truth_dependency"] is not False:
            raise RuntimeError("optimizer declared a ground-truth dependency")
        if o["solver"]["status"] != "OPTIMAL_EXACT_SEARCH":
            raise RuntimeError(f"optimizer status {o['solver']['status']}")
        if o["best_portfolio"]["intervention_codes"] != ["TOOL_RECALIBRATION"]:
            raise RuntimeError(f"unexpected portfolio: {o['best_portfolio']['intervention_codes']}")
        if o["best_portfolio"]["engineering_assumptions"]["total_one_time_cost_usd"] > 25000:
            raise RuntimeError("budget constraint violated")
        return f"optimal={o['best_portfolio']['intervention_codes'][0]}; evaluated={o['solver']['evaluated_portfolios']}/64 after safe pruning; constraints honored"

    results.append(check("Improvement portfolio optimizer", optimizer_check))

    def milp_oracle_check():
        from kaizen_factory.models import FactoryConfig
        from kaizen_factory.simulator import simulate_factory
        from kaizen_optimizer import solve_improvement_portfolio
        r = simulate_factory(FactoryConfig(seed=42, units=700), "tool_calibration_drift")
        o = solve_improvement_portfolio(r.records, r.activation_unit)
        m = o["solver"]["milp"]
        if m["status"] != "OPTIMAL" or not m["success"]:
            raise RuntimeError(f"MILP failed: {m}")
        if o["solver"]["oracle_agreement"] is not True:
            raise RuntimeError("MILP and exact nonlinear oracle disagree on objective")
        if m["selected_intervention_codes"] != o["best_portfolio"]["intervention_codes"]:
            raise RuntimeError("MILP and oracle selected different reference portfolios")
        return f"MILP={m['selected_intervention_codes']}; exact oracle agrees; variables={m['binary_variables']}"

    results.append(check("V1 MILP + exact oracle", milp_oracle_check))

    def data_contract_check():
        from kaizen_data import contract_document, normalize_records, build_external_result
        from kaizen_factory.models import FactoryConfig
        from kaizen_factory.simulator import simulate_factory
        r = simulate_factory(FactoryConfig(seed=91, units=120), "tool_calibration_drift")
        rows = [dict(x) for x in r.records]
        for x in rows:
            x["equipment_id"] = x.pop("machine_id")
            x.pop("unit_index", None)
            x.pop("total_processing_s", None)
        normalized, report = normalize_records(rows)
        if not report["readiness"]["full_engine_ready"]:
            raise RuntimeError("canonical mapping did not reach full-engine readiness")
        if report["fabricated_fields"]:
            raise RuntimeError("adapter fabricated source fields")
        ext = build_external_result(normalized, activation_unit=r.activation_unit, line_name="External Cell", source_mode="LIVE")
        if ext.source_mode != "LIVE" or ext.ground_truth:
            raise RuntimeError("external truth boundary failed")
        c = contract_document()
        return f"contract={c['version']}; modes={','.join(c['source_modes'])}; full-engine fields={len(c['full_engine_required_fields'])}; fabricated=0"

    results.append(check("Manufacturing data contract", data_contract_check))

    def control_room_ui_check():
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "static" / "styles.css").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        required = ["mission", "measure", "operations", "diagnose", "decide", "validate", "data"]
        missing = [x for x in required if f'data-workspace-target="{x}"' not in html]
        if missing:
            raise RuntimeError(f"missing workspaces: {missing}")
        if ".workspace-section:not(.active-workspace)" not in css or "function setWorkspace(name" not in js:
            raise RuntimeError("workspace navigation/hiding contract missing")
        if "CAREER FAIR MODE" in html or "3-MINUTE RECRUITER DEMO" in html or "toggleCareerMode" in js or "career-mode" in css:
            raise RuntimeError("separate presentation mode should not exist in unified V1.0 UI")
        if "DATA / INTEGRATION" not in html or "ENGINEERING REPORT" not in html:
            raise RuntimeError("V1 unified product/data controls missing")
        return "7 workspaces; one unified Mission Control interface + Data workspace ready"

    results.append(check("V1 control-room UI", control_room_ui_check))

    def control_plan_check():
        from kaizen_control import build_control_plan
        from kaizen_factory.models import FactoryConfig
        from kaizen_factory.simulator import simulate_factory
        r = simulate_factory(FactoryConfig(seed=42, units=600), "tool_calibration_drift")
        c = build_control_plan(r.records, r.activation_unit, line_name=r.config.line_name, seed=r.config.seed)
        if c["state"] != "CONTROL_PLAN_READY":
            raise RuntimeError("control plan not ready")
        if c["handoff"]["realized_benefits_verified"]:
            raise RuntimeError("control plan fabricated realized benefits")
        if c["benefits_verification"]["minimum_stabilization_window_units"] < 100:
            raise RuntimeError("stabilization window too small")
        return f"metric={c['monitoring']['primary_metric']}; stabilization={c['benefits_verification']['minimum_stabilization_window_units']} units; realized benefits not fabricated"

    results.append(check("DMAIC control + benefits verification", control_plan_check))

    def ai_contract_check():
        from kaizen_ai.engine import ask_kaizen
        from kaizen_ai.models import AIExecutionResult, GroundedAIResponse, ToolTraceEntry
        from kaizen_factory.models import FactoryConfig
        from kaizen_factory.simulator import simulate_factory

        class FixtureProvider:
            name = "diagnostic-fixture"
            model = "offline-contract"
            def run(self, *, question, toolbox, mode):
                inv = toolbox.call("get_investigation_summary", {})
                ev = toolbox.call("get_evidence_ledger", {"hypothesis_code": inv["top_suspect"]["code"]})
                ids = [x["evidence_id"] for x in ev["evidence"][:2]]
                return AIExecutionResult(
                    response=GroundedAIResponse(
                        mode=mode, headline="Grounded diagnostic response",
                        answer="M2 is the leading observational suspect; causal confirmation remains locked.",
                        confidence_language="Strong observational support; not causal proof.", evidence_ids=ids,
                        contradictory_evidence=["Competing explanations remain in the ledger."],
                        assumptions=["Observable-data quality remains adequate."],
                        unresolved_questions=["Controlled intervention evidence is absent."],
                        recommended_next_actions=["Run a controlled intervention/DOE."],
                    ),
                    tool_trace=[ToolTraceEntry(tool="get_investigation_summary", arguments={}, result_summary="leader=M2")],
                    provider=self.name, model=self.model,
                )

        r = simulate_factory(FactoryConfig(seed=42, units=700), "tool_calibration_drift")
        out = ask_kaizen(r.records, r.activation_unit, "Why M2?", provider=FixtureProvider())
        if out.truth_dependency or out.causal_confirmation_unlocked:
            raise RuntimeError("AI guardrail regression")
        if not out.response.evidence_ids:
            raise RuntimeError("AI evidence validation missing")
        return f"tool-grounded response accepted; {len(out.response.evidence_ids)} ledger IDs validated; truth boundary intact"

    results.append(check("Gemini copilot contract", ai_contract_check))

    def ai_tool_null_safety_check():
        from kaizen_ai.tools import EngineeringToolbox
        from kaizen_factory.models import FactoryConfig
        from kaizen_factory.simulator import simulate_factory
        r = simulate_factory(FactoryConfig(seed=42, units=700), "tool_calibration_drift")
        box = EngineeringToolbox(r.records, r.activation_unit, seed=r.config.seed, line_name=r.config.line_name)
        o = box.call("solve_improvement_portfolio", {
            "budget_usd": 900, "max_downtime_hours": 8,
            "min_good_throughput_uph": None, "max_defect_rate_pct": None,
            "annual_volume_units": None, "effectiveness": None,
            "demand_multiplier": None, "min_evidence_score": None,
        })
        if o["constraints"]["min_good_throughput_uph"] != 80.0:
            raise RuntimeError("null/default normalization failed")
        return f"optional null arguments normalized; budget={o['constraints']['budget_usd']:.0f}; status={o['solver']['status']}"

    results.append(check("Gemini tool argument null-safety", ai_tool_null_safety_check))

    def ai_reference_namespace_check():
        from kaizen_ai.engine import ask_kaizen
        from kaizen_ai.models import AIExecutionResult, GroundedAIResponse, ToolTraceEntry
        from kaizen_factory.models import FactoryConfig
        from kaizen_factory.simulator import simulate_factory

        class NamespaceFixtureProvider:
            name = "diagnostic-namespace-fixture"
            model = "gemini-3.5-flash-lite"
            def run(self, *, question, toolbox, mode):
                inv = toolbox.call("get_investigation_summary", {})
                ev = toolbox.call("get_evidence_ledger", {"hypothesis_code": inv["top_suspect"]["code"]})
                real_id = ev["evidence"][0]["evidence_id"]
                return AIExecutionResult(
                    response=GroundedAIResponse(
                        mode=mode, headline="Namespace normalization diagnostic",
                        answer="Recognized engineering codes are references, not evidence IDs.",
                        confidence_language="Offline contract test.",
                        evidence_ids=[real_id, "MACHINE_TORQUE_BIAS", "GAGE_MEASUREMENT_DRIFT", "GAGE_RECALIBRATION"],
                        engineering_references=["G1", "M2", "F4", "Calibration"],
                        contradictory_evidence=[], assumptions=[], unresolved_questions=[], recommended_next_actions=[],
                    ),
                    tool_trace=[ToolTraceEntry(tool="get_investigation_summary", arguments={}, result_summary="leader=M2")],
                    provider=self.name, model=self.model,
                )

        r = simulate_factory(FactoryConfig(seed=42, units=700), "tool_calibration_drift")
        out = ask_kaizen(r.records, r.activation_unit, "Budget decision", provider=NamespaceFixtureProvider())
        if out.response.evidence_ids != ["EVD-0001"]:
            raise RuntimeError(f"evidence namespace normalization failed: {out.response.evidence_ids}")
        expected = {"MACHINE_TORQUE_BIAS", "GAGE_MEASUREMENT_DRIFT", "GAGE_RECALIBRATION", "G1", "M2", "F4", "Calibration"}
        if not expected.issubset(set(out.response.engineering_references)):
            raise RuntimeError(f"engineering reference normalization failed: {out.response.engineering_references}")
        return f"runtime assets + misfiled model codes normalized; evidence={out.response.evidence_ids[0]}; engineering_refs={len(out.response.engineering_references)}"

    results.append(check("Gemini reference namespace", ai_reference_namespace_check))

    def ai_semantic_grounding_check():
        from kaizen_ai.engine import ask_kaizen
        from kaizen_ai.models import AIExecutionResult, GroundedAIResponse, ToolTraceEntry
        from kaizen_factory.models import FactoryConfig
        from kaizen_factory.simulator import simulate_factory

        class WrongNarrativeProvider:
            name = "diagnostic-semantic-fixture"
            model = "offline-contract"
            def run(self, *, question, toolbox, mode):
                solved = toolbox.call("solve_improvement_portfolio", {
                    "budget_usd": 900, "max_downtime_hours": 8, "min_good_throughput_uph": 80
                })
                return AIExecutionResult(
                    response=GroundedAIResponse(
                        mode=mode, headline="Implement M2 recalibration",
                        answer="TOOL_RECALIBRATION satisfies the $900 budget.",
                        confidence_language="High confidence.", evidence_ids=[],
                        engineering_references=["TOOL_RECALIBRATION", "M2"],
                        contradictory_evidence=[], assumptions=[], unresolved_questions=[],
                        recommended_next_actions=["Recalibrate M2 now."],
                    ),
                    tool_trace=[ToolTraceEntry(
                        tool="solve_improvement_portfolio",
                        arguments={"budget_usd": 900, "max_downtime_hours": 8, "min_good_throughput_uph": 80},
                        result_summary=f"optimizer={solved['solver']['status']}",
                    )],
                    provider=self.name, model=self.model,
                )

        r = simulate_factory(FactoryConfig(seed=42, units=700), "tool_calibration_drift")
        out = ask_kaizen(
            r.records, r.activation_unit,
            "I have a $900 budget, maximum 8 hours downtime, and need at least 80 good units per hour. What should I do?",
            provider=WrongNarrativeProvider(), seed=r.config.seed, line_name=r.config.line_name,
        )
        if "INFEASIBLE" not in out.response.answer:
            raise RuntimeError("optimizer result did not override contradictory Gemini prose")
        if "satisfies the $900 budget" in out.response.answer:
            raise RuntimeError("contradictory Gemini budget claim survived semantic grounding")
        if any("Recalibrate M2 now" in x for x in out.response.recommended_next_actions):
            raise RuntimeError("unsafe infeasible recommendation survived semantic grounding")
        return "hard optimizer facts override contradictory LLM prose; unsafe action removed"

    results.append(check("Gemini semantic grounding", ai_semantic_grounding_check))

    def ai_orchestration_bound_check():
        from dataclasses import dataclass
        from kaizen_ai.provider import GeminiInteractionsProvider
        from kaizen_ai.models import GroundedAIResponse
        from kaizen_ai.tools import EngineeringToolbox
        from kaizen_factory.models import FactoryConfig
        from kaizen_factory.simulator import simulate_factory

        @dataclass
        class Step:
            type: str
            name: str = ""
            arguments: dict | None = None
            id: str = ""

        class Interaction:
            def __init__(self, id, steps=None, output_text=None):
                self.id = id
                self.steps = steps or []
                self.output_text = output_text

        class Interactions:
            def __init__(self):
                self.calls = []
            def create(self, **kwargs):
                self.calls.append(kwargs)
                n = len(self.calls)
                if n == 1:
                    return Interaction("diag-1", [Step("function_call", "get_investigation_summary", {}, "diag-call-1")])
                if n == 2:
                    return Interaction("diag-2", [Step("function_call", "solve_improvement_portfolio", {"budget_usd": 900, "max_downtime_hours": 8, "min_good_throughput_uph": 80}, "diag-call-2")])
                if "tools" in kwargs:
                    return Interaction(f"diag-{n}", [Step("function_call", "solve_improvement_portfolio", {"budget_usd": 900, "max_downtime_hours": 8, "min_good_throughput_uph": 80}, f"diag-call-{n}")])
                payload = GroundedAIResponse(
                    headline="Bounded synthesis", answer="No feasible portfolio under the supplied constraints.",
                    confidence_language="Exact within modeled constraints; not causal proof.", evidence_ids=[],
                    engineering_references=["TOOL_RECALIBRATION"], contradictory_evidence=[], assumptions=[],
                    unresolved_questions=[], recommended_next_actions=["Increase budget or relax a hard constraint."],
                ).model_dump_json()
                return Interaction("diag-final", [], payload)

        class Client:
            def __init__(self): self.interactions = Interactions()

        r = simulate_factory(FactoryConfig(seed=42, units=700), "tool_calibration_drift")
        box = EngineeringToolbox(r.records, r.activation_unit)
        client = Client()
        out = GeminiInteractionsProvider(model="gemini-test", client=client).run(
            question="I have a $900 budget, maximum 8 hours downtime, and need at least 80 good units per hour.",
            toolbox=box, mode="ASK",
        )
        if len(client.interactions.calls) != 3:
            raise RuntimeError(f"unexpected model-call count: {len(client.interactions.calls)}")
        if "tools" in client.interactions.calls[-1]:
            raise RuntimeError("final synthesis still exposed tools")
        if out.response.headline != "Bounded synthesis":
            raise RuntimeError("forced synthesis did not complete")
        return "optimizer closes tools; final synthesis forced in 3 model turns; no depth failure"

    results.append(check("Gemini bounded orchestration", ai_orchestration_bound_check))

    def ai_model_routing_check():
        from kaizen_ai import ai_status
        a = ai_status()
        if a["model"] != "gemini-3.5-flash-lite":
            raise RuntimeError(f"unexpected default model: {a['model']}")
        if not a.get("quota_fallback"):
            raise RuntimeError("quota fallback is disabled")
        if "gemini-3.1-flash-lite" not in a.get("model_chain", []):
            raise RuntimeError("fallback chain incomplete")
        return f"primary={a['model']}; chain={' -> '.join(a['model_chain'])}; quota fallback enabled"

    results.append(check("Gemini model routing", ai_model_routing_check))

    def ai_runtime_check():
        from kaizen_ai import ai_status
        a = ai_status()
        return f"sdk={'ready' if a['sdk_available'] else 'not installed in this interpreter'}; key={'present' if a['key_present'] else 'not configured'}; live AI={'ready' if a['configured'] else 'safely disabled'}"

    results.append(check("Gemini runtime status", ai_runtime_check))

    def active_investigation_check():
        from kaizen_active import build_active_investigation_overview
        from kaizen_factory.models import FactoryConfig
        from kaizen_factory.simulator import simulate_factory
        strong = simulate_factory(FactoryConfig(seed=42, units=700), "tool_calibration_drift")
        a = build_active_investigation_overview(strong.records, strong.activation_unit)
        if a["uncertainty"]["state"] != "STRONG_SUSPECT":
            raise RuntimeError("strong reference case was not retained as a strong suspect")
        if a["value_of_information"]["recommended_next_measurement"]["hypothesis_code"] != "MACHINE_TORQUE_BIAS":
            raise RuntimeError("VOI did not prioritize the current decision-relevant machine probe")
        weak = simulate_factory(FactoryConfig(seed=0, units=100), "random")
        w = build_active_investigation_overview(weak.records, weak.activation_unit)
        if w["uncertainty"]["state"] != "I_DONT_KNOW":
            raise RuntimeError("small ambiguous blind sample failed I DON'T KNOW policy")
        return f"seed42={a['uncertainty']['state']}; small-blind={w['uncertainty']['state']}; VOI={a['value_of_information']['recommended_next_measurement']['code']}"

    results.append(check("Active investigation + I DON'T KNOW", active_investigation_check))

    def controlled_doe_check():
        from kaizen_active import build_experiment_design, execute_controlled_experiment
        from kaizen_factory.models import FactoryConfig
        from kaizen_factory.simulator import simulate_factory
        r = simulate_factory(FactoryConfig(seed=42, units=700), "tool_calibration_drift")
        d = build_experiment_design(r.records, r.activation_unit)
        good = execute_controlled_experiment(r.records, r.activation_unit, r.scenario_code, d["experiment_code"], seed=42)
        bad = execute_controlled_experiment(r.records, r.activation_unit, r.scenario_code, "DOE_GAGE_RECALIBRATION", seed=42)
        if not good["causal_confirmation"]["passed"]:
            raise RuntimeError("correct predeclared DOE failed reference confirmation")
        if bad["causal_confirmation"]["passed"]:
            raise RuntimeError("wrong DOE incorrectly unlocked Level 5")
        if good["truth_boundary"]["ground_truth_exposed_in_output"]:
            raise RuntimeError("controlled experiment leaked ground truth")
        return f"correct DOE L5=UNLOCKED; wrong DOE L5=LOCKED; p={good['aggregate_results']['p_value']:.3g}; d={good['aggregate_results']['cohen_d']:.2f}"

    results.append(check("Controlled synthetic DOE causal gate", controlled_doe_check))

    def human_vs_ai_check():
        from kaizen_active import freeze_human_prediction, score_human_prediction
        from kaizen_factory.models import FactoryConfig
        from kaizen_factory.simulator import simulate_factory
        r = simulate_factory(FactoryConfig(seed=42, units=700), "tool_calibration_drift")
        p = freeze_human_prediction(r.records, r.activation_unit, "MACHINE_TORQUE_BIAS")
        s = score_human_prediction(p, r.scenario_code)
        if s["score"] != 100.0:
            raise RuntimeError("reference human prediction scoring failed")
        return f"prediction frozen pre-reveal; reference score={s['score']:.0f}% ({s['dimensions_correct']}/4)"

    results.append(check("Human vs AI scoring", human_vs_ai_check))

    def launcher_check():
        import importlib.util
        spec = importlib.util.spec_from_file_location("kaizen_launch_diag", ROOT / "scripts" / "launch.py")
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        if module.START_PORT > module.END_PORT:
            raise RuntimeError(f"invalid port range {module.START_PORT}-{module.END_PORT}")
        port = module.first_free_port()
        if not (module.START_PORT <= port <= module.END_PORT):
            raise RuntimeError(f"selected port {port} is out of range")
        return f"range={module.START_PORT}-{module.END_PORT}; first free port={port}; startup range valid"

    results.append(check("Launcher port range", launcher_check))

    results.append(check("API import", lambda: importlib.import_module("app.main").app.version))

    passed = sum(results)
    total = len(results)
    print(f"\nDiagnostics: {passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
