from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Protocol

from .models import AIExecutionResult, GroundedAIResponse, ToolTraceEntry
from .tools import TOOL_DECLARATIONS, EngineeringToolbox


def _load_local_env() -> None:
    """Load simple KEY=VALUE entries from project .env without exposing secrets."""
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value


_load_local_env()

# V0.8.2 deliberately defaults to Flash-Lite. The engineering math already lives inside
# KAIZEN; Gemini's job is orchestration/explanation, where lower latency and higher quota
# headroom matter more than using the largest model on every turn.
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip() or "gemini-3.5-flash-lite"
_DEFAULT_FALLBACK_TEXT = os.getenv(
    "GEMINI_FALLBACK_MODELS",
    "gemini-3.5-flash-lite,gemini-3.1-flash-lite,gemini-2.5-flash-lite",
)
DEFAULT_FALLBACK_MODELS = tuple(
    x.strip() for x in _DEFAULT_FALLBACK_TEXT.split(",") if x.strip()
)

SYSTEM_INSTRUCTION = """
You are KAIZEN AI, an evidence-grounded manufacturing improvement copilot.
You reason over a Lean Six Sigma + Industrial Engineering analytical system.

NON-NEGOTIABLE RULES:
1. Use KAIZEN engineering functions for process facts, statistics, simulation, costs, throughput and optimization. Never invent calculations.
2. You do not have access to sealed simulator ground truth, scenario code, latent variables or causal labels. Never ask for them.
3. `evidence_ids` may contain ONLY literal evidence-ledger IDs in EVD-#### form that exist in tool results. Hypothesis codes (for example MACHINE_TORQUE_BIAS), intervention codes (for example GAGE_RECALIBRATION), and exact runtime entities returned by KAIZEN tools (for example M2, G1, F4, supplier lots or station names) belong in `engineering_references`, never in `evidence_ids`. Never fabricate EVD IDs, p-values, effect sizes, costs or model outputs.
4. Observational evidence, an LLM explanation, and a counterfactual simulation do NOT confirm causality. Only the authorized V0.9 controlled synthetic DOE endpoint may unlock L5 inside the Hidden Factory benchmark; never claim real-world causal validation.
5. If the V0.9 active-investigation tool says I_DONT_KNOW, preserve that conclusion. 'I don't know yet' is an acceptable engineering conclusion and must not be upgraded by prose alone.
6. Surface contradictory evidence and assumptions, not only supporting evidence.
7. Do not claim a human approved an action unless a tool explicitly says so.
8. Your final answer must comply with the structured response schema.
9. Optional tool parameters may be omitted. Do not send null unless there is a real semantic need for null; KAIZEN defaults omitted optional parameters safely.
10. Deterministic tool outputs are authoritative. If the exact optimizer says INFEASIBLE, you must not describe any action as feasible or as satisfying the constraints. Never restate a cost, throughput, defect rate, downtime, p-value, confidence interval or solver status in conflict with the tool payload.
""".strip()


class Provider(Protocol):
    name: str
    model: str
    def run(self, *, question: str, toolbox: EngineeringToolbox, mode: str) -> AIExecutionResult: ...


class DeterministicEvidenceProvider:
    """Keyless, tool-grounded fallback used when Gemini is unavailable."""

    name = "KAIZEN deterministic evidence engine"
    model = "engineering-rules-v1"

    def run(self, *, question: str, toolbox: EngineeringToolbox, mode: str) -> AIExecutionResult:
        investigation = toolbox.call("get_investigation_summary", {})
        leader = investigation["top_suspect"]
        ledger = toolbox.call(
            "get_evidence_ledger", {"hypothesis_code": leader["code"]}
        )
        evidence_ids = [row["evidence_id"] for row in ledger.get("evidence", [])[:3]]
        red_team = mode.upper() == "RED_TEAM"
        headline = (
            f"Challenge review for {leader['target']}"
            if red_team
            else f"{leader['target']} is the leading observational suspect"
        )
        answer = (
            f"KAIZEN's deterministic investigation ranks {leader['target']} first "
            f"with evidence score {leader.get('evidence_score', 'not reported')}. "
            "This is an evidence-grounded diagnostic readout, not causal confirmation. "
            "Review the cited ledger entries and run a controlled intervention before release."
        )
        return AIExecutionResult(
            response=GroundedAIResponse(
                mode=mode.upper(),
                headline=headline,
                answer=answer,
                confidence_language="Tool-grounded observational evidence; causal authority remains locked.",
                evidence_ids=evidence_ids,
                engineering_references=[leader["code"], leader["target"]],
                contradictory_evidence=[
                    "Alternative hypotheses and confounders remain possible until controlled evidence is collected."
                ],
                assumptions=[
                    "The current measurement system and source provenance remain valid for this run."
                ],
                unresolved_questions=[
                    "Will a controlled intervention reproduce the predicted improvement?"
                ],
                recommended_next_actions=[
                    "Inspect the evidence ledger, then authorize a bounded controlled experiment or DOE."
                ],
            ),
            tool_trace=[
                ToolTraceEntry(
                    tool="get_investigation_summary",
                    arguments={},
                    result_summary=f"leader={leader['target']} evidence={leader.get('evidence_score')}",
                ),
                ToolTraceEntry(
                    tool="get_evidence_ledger",
                    arguments={"hypothesis_code": leader["code"]},
                    result_summary=f"evidence_rows={len(ledger.get('evidence', []))}",
                ),
            ],
            provider=self.name,
            model=self.model,
        )


def key_configured() -> bool:
    return bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))


def sdk_available() -> bool:
    try:
        import google.genai  # noqa: F401
        return True
    except Exception:
        return False


def _dedupe_models(primary: str, fallbacks: tuple[str, ...] | list[str]) -> list[str]:
    out: list[str] = []
    for model in [primary, *fallbacks]:
        m = str(model).strip()
        if m and m not in out:
            out.append(m)
    return out




def _initial_required_tool(question: str, mode: str) -> str:
    """Route the first Gemini tool call to the smallest authoritative packet for the task."""
    text = question.casefold()
    if mode == "RED_TEAM" or any(term in text for term in (
        "why", "suspect", "evidence", "strongest", "argues against", "against it", "confound", "red team"
    )):
        return "get_diagnosis_evidence_packet"
    if any(term in text for term in (
        "budget", "downtime", "good units", "good throughput", "portfolio", "hard constraint", "what should i do"
    )):
        return "solve_improvement_portfolio"
    if any(term in text for term in (
        "what should we measure", "next measurement", "next test", "reduce uncertainty", "value of information", "don't know", "dont know"
    )):
        return "get_active_investigation_plan"
    if any(term in text for term in (
        "design experiment", "design a doe", "doe plan", "experiment plan", "causal test"
    )):
        return "get_experiment_design"
    return "get_investigation_summary"


def ai_status() -> dict[str, Any]:
    configured = key_configured() and sdk_available()
    model_chain = _dedupe_models(DEFAULT_MODEL, DEFAULT_FALLBACK_MODELS)
    return {
        "provider": "Google Gemini",
        "model": DEFAULT_MODEL,
        "fallback_models": model_chain[1:],
        "model_chain": model_chain,
        "configured": configured,
        "available": True,
        "deterministic_fallback": True,
        "active_mode": "gemini" if configured else "deterministic-evidence",
        "key_present": key_configured(),
        "sdk_available": sdk_available(),
        "sdk": "google-genai",
        "api": "Interactions API",
        "function_calling": True,
        "structured_output": True,
        "quota_fallback": True,
        "ground_truth_dependency": False,
        "causal_confirmation_unlocked": False,
        "key_policy": "Use GEMINI_API_KEY or GOOGLE_API_KEY environment variable. Never place secrets in source code.",
    }


def _result_summary(value: Any) -> str:
    if isinstance(value, dict):
        if value.get("ok") is False and "error" in value:
            return f"tool_error={value['error']}"
        if "top_suspect" in value:
            t = value["top_suspect"]
            return f"leader={t.get('target')} evidence={t.get('evidence_score')} status={t.get('status')}"
        if "solver" in value:
            return f"optimizer={value['solver'].get('status')} feasible={value.get('feasible_portfolio_count')}"
        if "counterfactual" in value:
            c = value["counterfactual"]
            return f"defect={c.get('defect_rate')} good_uph={c.get('good_throughput_units_per_hour')}"
        if "evidence" in value:
            return f"evidence_rows={value.get('count', len(value.get('evidence', [])))}"
        return ", ".join(list(value.keys())[:6])
    return str(value)[:160]


def _redact_secret(text: str) -> str:
    redacted = str(text)
    for key_name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        value = os.getenv(key_name)
        if value:
            redacted = redacted.replace(value, "[REDACTED]")
    return redacted


def _status_code(exc: Exception) -> int | None:
    for attr in ("status_code", "code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
        try:
            if value is not None and str(value).isdigit():
                return int(value)
        except Exception:
            pass
    # Some google-genai exception wrappers put the HTTP code only in the message.
    text = str(exc).lower()
    for code in (429, 500, 502, 503, 504, 401, 403, 404, 400):
        if f"error code: {code}" in text or f"http {code}" in text or f"code={code}" in text:
            return code
    return None


def _is_transient(exc: Exception) -> bool:
    code = _status_code(exc)
    name = type(exc).__name__.lower()
    text = str(exc).lower()
    return code in {500, 502, 503, 504} or "servererror" in name or "temporar" in text or "unavailable" in text


def _is_quota_error(exc: Exception) -> bool:
    code = _status_code(exc)
    text = str(exc).lower()
    return code == 429 or "resource_exhausted" in text or "quota exceeded" in text or "ratelimiterror" in type(exc).__name__.lower()


class GeminiInteractionsProvider:
    name = "Google Gemini"

    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        fallback_models: list[str] | tuple[str, ...] | None = None,
        client: Any | None = None,
    ):
        self.model = model
        self.fallback_models = tuple(DEFAULT_FALLBACK_MODELS if fallback_models is None else fallback_models)
        self.model_chain = _dedupe_models(self.model, self.fallback_models)
        self.active_model = self.model_chain[0]
        if client is not None:
            self.client = client
        else:
            if not key_configured():
                raise RuntimeError("Gemini is not configured. Set GEMINI_API_KEY or GOOGLE_API_KEY and restart KAIZEN.")
            try:
                from google import genai
            except Exception as exc:
                raise RuntimeError("google-genai SDK is not installed") from exc
            self.client = genai.Client()

    def _model_attempt_order(self) -> list[str]:
        # Once a fallback succeeds, keep using it for the rest of the same orchestrated request.
        return _dedupe_models(self.active_model, tuple(m for m in self.model_chain if m != self.active_model))

    def _create_interaction(self, **kwargs):
        """Normalize SDK/API failures, retry transient failures, and fall back across models on quota exhaustion."""
        kwargs = dict(kwargs)
        kwargs.pop("model", None)
        last_exc: Exception | None = None
        attempted: list[str] = []

        for candidate in self._model_attempt_order():
            attempted.append(candidate)
            # Retry one genuinely transient 5xx failure on the same candidate. A quota 429 is
            # not retried pointlessly; it immediately advances to the next configured model.
            for attempt in range(2):
                try:
                    interaction = self.client.interactions.create(model=candidate, **kwargs)
                    self.active_model = candidate
                    return interaction
                except Exception as exc:  # SDK error classes vary by google-genai release.
                    last_exc = exc
                    if _is_quota_error(exc):
                        break
                    if attempt == 0 and _is_transient(exc):
                        time.sleep(0.5)
                        continue
                    code = _status_code(exc)
                    code_text = f" HTTP {code}" if code is not None else ""
                    raise RuntimeError(
                        f"Gemini API request failed{code_text} on {candidate} ({type(exc).__name__}): {_redact_secret(str(exc))}"
                    ) from exc

            # Quota failure: try the next independent model quota in the configured chain.
            if last_exc is not None and _is_quota_error(last_exc):
                continue

        if last_exc is not None:
            code = _status_code(last_exc)
            code_text = f" HTTP {code}" if code is not None else ""
            attempted_text = ", ".join(attempted)
            raise RuntimeError(
                f"Gemini API quota exhausted{code_text} across configured models [{attempted_text}]. "
                f"Check per-model limits in Google AI Studio or wait for quota reset. "
                f"Last provider error: {_redact_secret(str(last_exc))}"
            ) from last_exc
        raise RuntimeError("Gemini API request failed before any model was attempted")

    def _parse_final_interaction(
        self,
        interaction: Any,
        *,
        mode: str,
        trace: list[ToolTraceEntry],
    ) -> AIExecutionResult:
        calls = [s for s in getattr(interaction, "steps", []) if getattr(s, "type", None) == "function_call"]
        if calls:
            raise RuntimeError("Gemini requested another engineering tool after KAIZEN closed the tool phase")
        text = getattr(interaction, "output_text", None)
        if not text:
            raise RuntimeError("Gemini returned neither a function call nor a final structured response")
        try:
            parsed = GroundedAIResponse.model_validate_json(text)
        except Exception as exc:
            raise RuntimeError(f"Gemini returned invalid structured output: {_redact_secret(str(exc))}") from exc
        parsed.mode = mode
        return AIExecutionResult(
            response=parsed,
            tool_trace=trace,
            provider=self.name,
            model=self.active_model,
            grounded=bool(trace),
            truth_dependency=False,
            causal_confirmation_unlocked=False,
        )

    @staticmethod
    def _tool_signature(name: str, arguments: dict[str, Any]) -> str:
        try:
            payload = json.dumps(arguments, sort_keys=True, separators=(",", ":"), default=str, allow_nan=False)
        except Exception:
            payload = repr(sorted(arguments.items()))
        return f"{name}:{payload}"

    def _continue_after_tool_results(
        self,
        *,
        interaction_id: str,
        function_results: list[dict[str, Any]],
        response_schema: dict[str, Any],
        close_tools: bool,
        close_reason: str = "",
    ):
        if close_tools:
            final_instruction = (
                SYSTEM_INSTRUCTION
                + "\n\nFINAL SYNTHESIS PHASE:\n"
                + "KAIZEN has closed the engineering-tool phase for this answer. "
                + "Use the tool results already present in the interaction history and produce the final structured response now. "
                + "Do not request additional tools, do not invent missing calculations, and explicitly state any unresolved uncertainty."
            )
            if close_reason:
                final_instruction += f"\nClosure reason: {close_reason}."
            return self._create_interaction(
                previous_interaction_id=interaction_id,
                input=function_results,
                system_instruction=final_instruction,
                generation_config={"thinking": {"thinking_level": "low"}},
                response_format={"type": "text", "mime_type": "application/json", "schema": response_schema},
            )

        return self._create_interaction(
            previous_interaction_id=interaction_id,
            input=function_results,
            tools=TOOL_DECLARATIONS,
            system_instruction=SYSTEM_INSTRUCTION,
            generation_config={"thinking": {"thinking_level": "low"}, "tool_choice": "auto"},
            response_format={"type": "text", "mime_type": "application/json", "schema": response_schema},
        )

    def run(self, *, question: str, toolbox: EngineeringToolbox, mode: str) -> AIExecutionResult:
        mode = mode.upper()
        if mode not in {"ASK", "RED_TEAM"}:
            raise ValueError("mode must be ASK or RED_TEAM")
        task = question.strip()
        if mode == "RED_TEAM":
            task = (
                "RED TEAM TASK: Construct the strongest evidence-grounded case against KAIZEN's current leading diagnosis and recommended action. "
                "Identify contradictory evidence, confounders, model assumptions, and what evidence could overturn the recommendation. "
                "Do not manufacture doubt: distinguish genuine weaknesses from well-supported findings.\n\nUser context: " + task
            )

        response_schema = GroundedAIResponse.model_json_schema()
        trace: list[ToolTraceEntry] = []
        result_cache: dict[str, dict[str, Any]] = {}
        seen_signatures: set[str] = set()

        max_tool_rounds = 4
        max_unique_tool_calls = 7
        terminal_decision_tools = {"solve_improvement_portfolio"}

        first_required_tool = _initial_required_tool(task, mode)
        interaction = self._create_interaction(
            input=task,
            tools=TOOL_DECLARATIONS,
            system_instruction=(
                SYSTEM_INSTRUCTION
                + "\n\nORCHESTRATION POLICY: Never call the same tool with the same arguments twice. "
                + "Use the minimum number of engineering tools needed. Once an exact portfolio optimization directly answers the user's constraints, synthesize the answer instead of requesting more tools. "
                + "For evidence/red-team questions, prefer the diagnosis evidence packet because it already contains the leading ledger rows, contradictions, confounders and causal gate."
            ),
            generation_config={
                "thinking": {"thinking_level": "low"},
                "tool_choice": {"allowed_tools": {"mode": "any", "tools": [first_required_tool]}},
            },
            response_format={"type": "text", "mime_type": "application/json", "schema": response_schema},
        )

        for tool_round in range(1, max_tool_rounds + 1):
            calls = [s for s in getattr(interaction, "steps", []) if getattr(s, "type", None) == "function_call"]
            if not calls:
                return self._parse_final_interaction(interaction, mode=mode, trace=trace)

            function_results: list[dict[str, Any]] = []
            round_signatures: list[str] = []
            round_has_new_information = False
            round_has_terminal_decision = False

            for call in calls:
                raw_args = getattr(call, "arguments", {}) or {}
                try:
                    arguments = dict(raw_args)
                except Exception:
                    arguments = {}

                signature = self._tool_signature(call.name, arguments)
                round_signatures.append(signature)
                was_cached = signature in result_cache

                if was_cached:
                    result = result_cache[signature]
                else:
                    try:
                        result = toolbox.call(call.name, arguments)
                    except Exception as exc:
                        result = {
                            "ok": False,
                            "error": f"{type(exc).__name__}: {str(exc)}",
                            "instruction": "Correct the tool arguments and retry. Do not invent a result.",
                        }
                    result_cache[signature] = result
                    seen_signatures.add(signature)
                    round_has_new_information = True

                summary = _result_summary(result)
                if was_cached:
                    summary = "cached-repeat; " + summary
                trace.append(ToolTraceEntry(tool=call.name, arguments=arguments, result_summary=summary))

                if call.name in terminal_decision_tools and not (isinstance(result, dict) and result.get("ok") is False):
                    round_has_terminal_decision = True

                function_results.append({
                    "type": "function_result",
                    "name": call.name,
                    "call_id": call.id,
                    "is_error": bool(isinstance(result, dict) and result.get("ok") is False),
                    "result": [{"type": "text", "text": json.dumps(result, default=str, allow_nan=False)}],
                })

            duplicate_only = bool(round_signatures) and not round_has_new_information
            unique_limit_hit = len(seen_signatures) >= max_unique_tool_calls
            round_limit_hit = tool_round >= max_tool_rounds

            close_tools = round_has_terminal_decision or duplicate_only or unique_limit_hit or round_limit_hit
            if round_has_terminal_decision:
                reason = "an exact improvement-portfolio result already answers the user's hard constraints"
            elif duplicate_only:
                reason = "Gemini repeated tool calls that produced no new engineering information"
            elif unique_limit_hit:
                reason = f"KAIZEN reached its {max_unique_tool_calls}-unique-tool evidence budget"
            elif round_limit_hit:
                reason = f"KAIZEN reached its {max_tool_rounds}-round orchestration budget"
            else:
                reason = ""

            interaction = self._continue_after_tool_results(
                interaction_id=interaction.id,
                function_results=function_results,
                response_schema=response_schema,
                close_tools=close_tools,
                close_reason=reason,
            )

            if close_tools:
                return self._parse_final_interaction(interaction, mode=mode, trace=trace)

        raise RuntimeError("KAIZEN orchestration ended unexpectedly before final synthesis")
