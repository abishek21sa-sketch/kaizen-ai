from __future__ import annotations

from typing import Any
import re

from .models import AIExecutionResult
from .provider import GeminiInteractionsProvider, Provider, ai_status
from .tools import EngineeringToolbox
from kaizen_investigator import build_investigation_overview
from kaizen_simulation import INTERVENTION_CATALOG
from kaizen_active.engine import PROBE_CATALOG, EXPERIMENT_PLANS


_OBSERVABLE_REFERENCE_FIELDS = (
    "machine_id",
    "gage_id",
    "fixture_id",
    "supplier",
    "supplier_lot",
    "operator_id",
    "product_variant",
    "defect_type",
)

_STATION_REFERENCES = {
    "Bearing Press",
    "Motor Assembly",
    "Adhesive Dispense",
    "Torque Fastening",
    "Calibration",
    "Functional Test",
    "Final Inspection",
}

_EVIDENCE_INTENT_TERMS = (
    "why",
    "suspect",
    "evidence",
    "strongest",
    "argues against",
    "against it",
    "confound",
    "confidence",
    "support",
)


def _add_reference(refs: set[str], value: Any) -> None:
    if value is None:
        return
    text = str(value).strip()
    if text:
        refs.add(text)


def _engineering_reference_catalog(
    records: list[dict[str, Any]],
    investigation: dict[str, Any],
    *,
    line_name: str,
) -> dict[str, str]:
    """Build a canonical, observable-only reference catalog for AI validation."""
    refs: set[str] = set()
    _add_reference(refs, line_name)
    refs.update(_STATION_REFERENCES)

    for code, meta in INTERVENTION_CATALOG.items():
        _add_reference(refs, code)
        _add_reference(refs, meta.get("label"))
        _add_reference(refs, meta.get("hypothesis_code"))

    for meta in PROBE_CATALOG.values():
        for key in ("code", "label", "hypothesis_code"):
            _add_reference(refs, meta.get(key))
    for code, meta in EXPERIMENT_PLANS.items():
        _add_reference(refs, code)
        _add_reference(refs, meta.get("experiment_code"))
        _add_reference(refs, meta.get("title"))

    for h in investigation.get("ranked_hypotheses", []):
        for key in ("code", "target", "title", "mechanism_class", "status", "causal_status"):
            _add_reference(refs, h.get(key))
        attribution = h.get("attribution") or {}
        for key in (
            "target",
            "target_type",
            "factor",
            "interaction_partner",
            "outcome",
            "direction",
        ):
            _add_reference(refs, attribution.get(key))

    for row in records:
        for field in _OBSERVABLE_REFERENCE_FIELDS:
            _add_reference(refs, row.get(field))
        shift = row.get("shift")
        if shift is not None:
            _add_reference(refs, f"Shift {shift}")

    return {ref.casefold(): ref for ref in refs}


def _canonical_engineering_reference(raw: Any, catalog: dict[str, str]) -> str | None:
    text = str(raw).strip()
    if not text:
        return None
    return catalog.get(text.casefold())


def _fmt_money(value: Any) -> str:
    try:
        return f"${float(value):,.0f}"
    except Exception:
        return str(value)


def _fmt_num(value: Any, digits: int = 2) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return str(value)


def _latest_tool_call(result: AIExecutionResult, tool_name: str) -> dict[str, Any] | None:
    for entry in reversed(result.tool_trace):
        if entry.tool == tool_name:
            return dict(entry.arguments or {})
    return None


def _apply_optimizer_semantic_guard(
    result: AIExecutionResult,
    toolbox: EngineeringToolbox,
) -> None:
    """Make exact optimizer output authoritative over Gemini narrative.

    Free-form LLM prose is not allowed to override hard feasibility, cost, downtime,
    throughput, quality or value results produced by the deterministic optimizer.
    If the optimizer was used, KAIZEN rewrites the decision core from the exact tool
    payload and preserves Gemini only for non-numeric assumptions/unknowns that do not
    contradict the deterministic result.
    """
    args = _latest_tool_call(result, "solve_improvement_portfolio")
    if args is None:
        return

    solved = toolbox.call("solve_improvement_portfolio", args)
    solver = solved.get("solver") or {}
    constraints = solved.get("constraints") or {}
    status = str(solver.get("status", "UNKNOWN"))

    budget = float(constraints.get("budget_usd", 0.0))
    downtime = float(constraints.get("max_downtime_hours", 0.0))
    min_good = float(constraints.get("min_good_throughput_uph", 0.0))
    max_defect = float(constraints.get("max_defect_rate", 1.0)) * 100.0

    if status == "INFEASIBLE":
        nearest = ((solved.get("infeasibility") or {}).get("nearest_portfolios") or [{}])[0]
        nearest_good = nearest.get("good_throughput_uph")
        nearest_defect = nearest.get("defect_rate")
        nearest_labels = nearest.get("labels") or []
        nearest_name = " + ".join(nearest_labels) if nearest_labels else "No action"

        result.response.headline = (
            f"No feasible intervention portfolio satisfies the {min_good:g} good-units/hour requirement"
        )
        eligible_codes = list(solver.get("eligible_intervention_codes") or [])
        budget_note = ""
        over_budget = []
        for code in eligible_codes:
            meta = INTERVENTION_CATALOG.get(code) or {}
            cost = meta.get("one_time_cost_usd")
            if isinstance(cost, (int, float)) and float(cost) > budget:
                over_budget.append(f"{meta.get('label', code)} costs {_fmt_money(cost)}")
        if over_budget:
            budget_note = " The leading evidence-eligible action is also pruned by budget: " + "; ".join(over_budget) + "."

        result.response.answer = (
            f"KAIZEN's exact portfolio optimizer returned INFEASIBLE under a budget of {_fmt_money(budget)}, "
            f"a maximum of {_fmt_num(downtime, 1)} hours planned downtime, and a minimum good-throughput floor of "
            f"{_fmt_num(min_good, 1)} units/hour. The nearest evaluated portfolio is {nearest_name}, at "
            f"{_fmt_num(nearest_good, 2)} good units/hour"
            + (f" and {_fmt_num(float(nearest_defect) * 100.0, 2)}% defects" if nearest_defect is not None else "")
            + ", so it still violates the throughput constraint."
            + budget_note
            + " No action or intervention is allowed to be described as satisfying these hard constraints unless the optimizer marks the portfolio feasible."
        )
        result.response.confidence_language = (
            "Definitive within KAIZEN's exact intervention catalog, simulation model and stated hard constraints; observational diagnosis is not causal proof."
        )
        result.response.contradictory_evidence = list(dict.fromkeys([
            f"The closest evaluated portfolio reaches only {_fmt_num(nearest_good, 2)} good units/hour versus the required {_fmt_num(min_good, 1)}.",
            *result.response.contradictory_evidence,
        ]))
        result.response.assumptions = list(dict.fromkeys([
            f"Hard constraints are budget <= {_fmt_money(budget)}, downtime <= {_fmt_num(downtime, 1)} h, good throughput >= {_fmt_num(min_good, 1)}/h, and defects <= {_fmt_num(max_defect, 1)}%.",
            "The optimizer considers only KAIZEN's registered intervention catalog and modeled counterfactual effects.",
            *result.response.assumptions,
        ]))
        result.response.recommended_next_actions = [
            "Relax at least one hard constraint or expand the intervention/resource catalog, then rerun the exact optimizer."
        ]
        return

    if status.startswith("OPTIMAL") or status == "OPTIMAL":
        best = solved.get("best_portfolio") or {}
        financials = solved.get("best_financials") or {}
        interventions = best.get("interventions") or []
        labels = [str(x.get("label")) for x in interventions if x.get("label")]
        selected = " + ".join(labels) if labels else "No action"
        eng = best.get("engineering_assumptions") or {}
        cf = best.get("counterfactual") or {}
        cost = eng.get("total_one_time_cost_usd")
        planned = eng.get("total_planned_downtime_hours")
        good = cf.get("good_throughput_units_per_hour")
        defect = cf.get("defect_rate")
        net = financials.get("first_year_net_value_usd")

        result.response.headline = f"Optimal modeled portfolio: {selected}"
        result.response.answer = (
            f"KAIZEN's exact optimizer selected {selected}. Modeled one-time cost is {_fmt_money(cost)}, planned downtime is "
            f"{_fmt_num(planned, 1)} hours, good throughput is {_fmt_num(good, 2)} units/hour, and defect rate is "
            f"{_fmt_num(float(defect) * 100.0, 2)}%."
            + (f" Evidence-adjusted first-year net value is {_fmt_money(net)}." if net is not None else "")
            + " These are modeled decision-support results under the stated constraints, not experimental causal confirmation."
        )
        result.response.confidence_language = (
            "Exact optimum within KAIZEN's enumerated intervention catalog and stated hard constraints; causal confirmation remains locked."
        )
        for item in interventions:
            for ref in (item.get("code"), item.get("label"), item.get("target"), item.get("hypothesis_code")):
                if ref:
                    result.response.engineering_references.append(str(ref))


def _enrich_evidence_and_red_team(
    result: AIExecutionResult,
    investigation: dict[str, Any],
    *,
    question: str,
    mode: str,
) -> None:
    """Backfill deterministic citations/limitations when the LLM under-populates them."""
    top = investigation.get("top_suspect") or {}
    top_code = top.get("code")
    evidence_intent = mode == "RED_TEAM" or any(term in question.casefold() for term in _EVIDENCE_INTENT_TERMS)

    if evidence_intent and top_code:
        top_ids = [
            str(e.get("evidence_id"))
            for e in investigation.get("evidence_ledger", [])
            if e.get("hypothesis_code") == top_code and e.get("evidence_id")
        ]
        if not result.response.evidence_ids:
            result.response.evidence_ids = top_ids[:3]

        for ref in (top_code, top.get("target")):
            if ref:
                result.response.engineering_references.append(str(ref))

    top_contradictions = [str(x) for x in (top.get("contradictory_evidence") or []) if str(x).strip()]
    top_assumptions = [str(x) for x in (top.get("assumptions") or []) if str(x).strip()]

    if top_contradictions:
        result.response.contradictory_evidence = list(dict.fromkeys([
            *result.response.contradictory_evidence,
            *top_contradictions,
        ]))
    if top_assumptions:
        result.response.assumptions = list(dict.fromkeys([
            *result.response.assumptions,
            *top_assumptions,
        ]))

    if mode == "RED_TEAM":
        # A Red Team card must never say "None identified" when the deterministic
        # investigator has explicit confounder signals. Surface them as limitations,
        # without promoting them to causes.
        for check in investigation.get("confounder_checks", []):
            factor = check.get("factor")
            level = check.get("level")
            test = check.get("test") or {}
            p = test.get("p_value")
            effect = test.get("effect")
            text = (
                f"Potential confounder: {factor}={level} also shifts post-incident"
                + (f" (p={p:.3g}" if isinstance(p, (int, float)) else "")
                + (f", standardized effect={effect:.3f})" if isinstance(effect, (int, float)) else (")" if isinstance(p, (int, float)) else "."))
                + " It is not promoted to a process cause without mechanism-specific evidence."
            )
            result.response.contradictory_evidence.append(text)
        result.response.contradictory_evidence = list(dict.fromkeys(result.response.contradictory_evidence))


def ask_kaizen(
    records: list[dict[str, Any]],
    activation_unit: int,
    question: str,
    *,
    mode: str = "ASK",
    provider: Provider | None = None,
    seed: int = 42,
    line_name: str = "Actuator Assembly Line A",
) -> AIExecutionResult:
    q = question.strip()
    if len(q) < 3:
        raise ValueError("Question must contain at least 3 characters")
    if len(q) > 4000:
        raise ValueError("Question must be 4,000 characters or fewer")

    toolbox = EngineeringToolbox(records, activation_unit, seed=seed, line_name=line_name)
    p = provider or GeminiInteractionsProvider()
    result = p.run(question=q, toolbox=toolbox, mode=mode)
    if not result.tool_trace:
        raise RuntimeError("AI response rejected: no KAIZEN engineering tool was called")

    inv = build_investigation_overview(records, activation_unit)

    # V0.8.7 semantic grounding: deterministic tool facts override LLM prose where
    # hard feasibility/numerical decisions are involved, and investigator evidence
    # backfills citations/limitations that smaller models may omit.
    _apply_optimizer_semantic_guard(result, toolbox)
    _enrich_evidence_and_red_team(result, inv, question=q, mode=mode.upper())

    valid_ids = {str(e["evidence_id"]).upper() for e in inv["evidence_ledger"]}
    reference_catalog = _engineering_reference_catalog(records, inv, line_name=line_name)

    cleaned_evidence_ids: list[str] = []
    cleaned_engineering_refs: set[str] = set()
    unknown_evidence_ids: set[str] = set()
    unknown_reference_tokens: set[str] = set()

    def consume_reference(raw: Any) -> None:
        ref = str(raw).strip()
        if not ref:
            return

        if re.fullmatch(r"EVD-\d{4}", ref, flags=re.IGNORECASE):
            evd = ref.upper()
            if evd in valid_ids:
                cleaned_evidence_ids.append(evd)
            else:
                unknown_evidence_ids.add(evd)
            return

        canonical = _canonical_engineering_reference(ref, reference_catalog)
        if canonical is not None:
            cleaned_engineering_refs.add(canonical)
            return

        unknown_reference_tokens.add(ref)

    for raw in result.response.evidence_ids:
        consume_reference(raw)
    for raw in result.response.engineering_references:
        consume_reference(raw)

    if unknown_evidence_ids:
        raise RuntimeError(
            f"AI response rejected: fabricated or unknown evidence IDs: {sorted(unknown_evidence_ids)}"
        )
    if unknown_reference_tokens:
        raise RuntimeError(
            f"AI response rejected: unknown engineering references: {sorted(unknown_reference_tokens)}"
        )

    result.response.evidence_ids = list(dict.fromkeys(cleaned_evidence_ids))
    result.response.engineering_references = sorted(cleaned_engineering_refs)

    result.truth_dependency = False
    result.causal_confirmation_unlocked = False
    return result


__all__ = ["ask_kaizen", "ai_status"]
