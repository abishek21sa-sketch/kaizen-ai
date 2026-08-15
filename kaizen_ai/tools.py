from __future__ import annotations

from typing import Any

from kaizen_investigator import build_investigation_overview
from kaizen_quality import build_quality_overview
from kaizen_ie import build_ie_overview
from kaizen_simulation import run_what_if, INTERVENTION_CATALOG
from kaizen_optimizer import solve_improvement_portfolio
from kaizen_active import build_active_investigation_overview, build_experiment_design


TOOL_DECLARATIONS = [
    {
        "type": "function",
        "name": "get_diagnosis_evidence_packet",
        "description": "Return the leading Statistical Investigator diagnosis together with its exact evidence-ledger rows, contradictory evidence, assumptions, confounder checks and causal gate. Use this for why/suspect/evidence/red-team questions instead of fetching these pieces separately.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "type": "function",
        "name": "get_investigation_summary",
        "description": "Return the ranked Statistical Investigator result, competing hypotheses, ambiguity and causal gate from observable production data only.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "type": "function",
        "name": "get_evidence_ledger",
        "description": "Return statistical evidence-ledger entries. Optionally filter by a hypothesis code such as MACHINE_TORQUE_BIAS.",
        "parameters": {
            "type": "object",
            "properties": {"hypothesis_code": {"type": "string", "description": "Optional exact hypothesis code."}},
        },
    },
    {
        "type": "function",
        "name": "get_quality_snapshot",
        "description": "Return Lean Six Sigma DEFINE/MEASURE evidence: data quality, COPQ, capability, MSA and SPC summary.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "type": "function",
        "name": "get_ie_snapshot",
        "description": "Return Industrial Engineering flow, takt, throughput, WIP, queue, capacity, line balance and OEE summary.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "type": "function",
        "name": "run_process_what_if",
        "description": "Execute a validated paired counterfactual replay for one intervention. Use this instead of inventing intervention effects.",
        "parameters": {
            "type": "object",
            "properties": {
                "intervention_code": {"type": "string", "enum": list(INTERVENTION_CATALOG)},
                "effectiveness": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "demand_multiplier": {"type": "number", "minimum": 0.5, "maximum": 1.75},
            },
            "required": ["intervention_code"],
        },
    },
    {
        "type": "function",
        "name": "solve_improvement_portfolio",
        "description": "Solve the exact six-action binary improvement portfolio under explicit budget, downtime, throughput, quality and evidence constraints.",
        "parameters": {
            "type": "object",
            "properties": {
                "budget_usd": {"type": "number", "minimum": 0},
                "max_downtime_hours": {"type": "number", "minimum": 0},
                "min_good_throughput_uph": {"type": "number", "minimum": 0},
                "max_defect_rate_pct": {"type": "number", "minimum": 0, "maximum": 100},
                "annual_volume_units": {"type": "integer", "minimum": 1},
                "effectiveness": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "demand_multiplier": {"type": "number", "minimum": 0.5, "maximum": 1.75},
                "min_evidence_score": {"type": "number", "minimum": 0, "maximum": 100},
            },
        },
    },
    {
        "type": "function",
        "name": "get_active_investigation_plan",
        "description": "Return KAIZEN V0.9 uncertainty state, I-DON'T-KNOW policy, ranked value-of-information probes and the recommended next measurement from observable evidence only.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "type": "function",
        "name": "get_experiment_design",
        "description": "Return the predeclared controlled synthetic DOE design for the current leading hypothesis. This designs but does not execute or authorize the experiment.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "type": "function",
        "name": "get_causal_gate",
        "description": "Return the correlation-not-causation gate and whether intervention/DOE confirmation is available.",
        "parameters": {"type": "object", "properties": {}},
    },
]


def _value_or_default(args: dict[str, Any], key: str, default: Any) -> Any:
    """Gemini may include optional JSON properties as null; null means 'use KAIZEN default'."""
    value = args.get(key, default)
    return default if value is None or value == "" else value


def _float_arg(args: dict[str, Any], key: str, default: float, *, minimum: float | None = None, maximum: float | None = None) -> float:
    raw = _value_or_default(args, key, default)
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be numeric") from exc
    if minimum is not None and value < minimum:
        raise ValueError(f"{key} must be >= {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{key} must be <= {maximum}")
    return value


def _int_arg(args: dict[str, Any], key: str, default: int, *, minimum: int | None = None) -> int:
    raw = _value_or_default(args, key, default)
    try:
        number = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be an integer") from exc
    if not number.is_integer():
        raise ValueError(f"{key} must be an integer")
    value = int(number)
    if minimum is not None and value < minimum:
        raise ValueError(f"{key} must be >= {minimum}")
    return value


class EngineeringToolbox:
    """Callable analytical tools exposed to Gemini. Never receives scenario code or ground truth."""

    def __init__(self, records: list[dict[str, Any]], activation_unit: int, *, seed: int = 42, line_name: str = "Actuator Assembly Line A"):
        self.records = records
        self.activation_unit = activation_unit
        self.seed = seed
        self.line_name = line_name
        self._inv: dict[str, Any] | None = None

    def _investigation(self) -> dict[str, Any]:
        if self._inv is None:
            self._inv = build_investigation_overview(self.records, self.activation_unit)
        return self._inv

    def call(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        args = arguments if isinstance(arguments, dict) else {}
        if name == "get_diagnosis_evidence_packet":
            inv = self._investigation()
            top = inv["top_suspect"]
            code = top.get("code")
            rows = [r for r in inv["evidence_ledger"] if r.get("hypothesis_code") == code]
            return {
                "top_suspect": top,
                "evidence": rows,
                "evidence_count": len(rows),
                "contradictory_evidence": top.get("contradictory_evidence", []),
                "assumptions": top.get("assumptions", []),
                "confounder_checks": inv.get("confounder_checks", []),
                "causality_gate": inv["causality_gate"],
                "evidence_state": inv["evidence_state"],
            }
        if name == "get_investigation_summary":
            inv = self._investigation()
            return {
                "top_suspect": inv["top_suspect"],
                "ranked_hypotheses": inv["ranked_hypotheses"],
                "causality_gate": inv["causality_gate"],
                "confounder_checks": inv["confounder_checks"],
                "evidence_state": inv["evidence_state"],
            }
        if name == "get_evidence_ledger":
            inv = self._investigation()
            code = _value_or_default(args, "hypothesis_code", None)
            rows = inv["evidence_ledger"]
            if code:
                rows = [r for r in rows if r["hypothesis_code"] == str(code)]
            return {"hypothesis_code": code, "count": len(rows), "evidence": rows}
        if name == "get_quality_snapshot":
            q = build_quality_overview(self.records, self.activation_unit, line_name=self.line_name, seed=self.seed)
            return {
                "problem_statement": q["define"]["project_charter"]["problem_statement"],
                "data_quality": q["data_quality"],
                "copq": q["pareto_copq"]["copq"],
                "pareto": q["pareto_copq"]["pareto"],
                "capability": q["capability"]["analyses"],
                "gage_rr": q["msa"]["crossed_gage_rr"],
                "spc": {
                    "torque_signal_count": q["spc"]["torque_error_imr"]["signal_count"],
                    "p_chart_signal_count": q["spc"]["defect_p_chart"]["signal_count"],
                    "baseline_policy": q["spc"]["baseline_policy"],
                },
            }
        if name == "get_ie_snapshot":
            ie = build_ie_overview(self.records, self.activation_unit)
            return {
                "takt": ie["takt"],
                "flow": ie["flow"],
                "queueing": ie["queueing"],
                "capacity": ie["capacity"],
                "line_balance": ie["line_balance"],
                "oee": ie["oee"],
            }
        if name == "run_process_what_if":
            code = str(_value_or_default(args, "intervention_code", ""))
            if code not in INTERVENTION_CATALOG:
                raise ValueError("Unknown intervention_code")
            return run_what_if(
                self.records,
                self.activation_unit,
                code,
                effectiveness=_float_arg(args, "effectiveness", 1.0, minimum=0.0, maximum=1.0),
                demand_multiplier=_float_arg(args, "demand_multiplier", 1.0, minimum=0.5, maximum=1.75),
            )
        if name == "solve_improvement_portfolio":
            return solve_improvement_portfolio(
                self.records,
                self.activation_unit,
                budget_usd=_float_arg(args, "budget_usd", 25_000.0, minimum=0.0),
                max_downtime_hours=_float_arg(args, "max_downtime_hours", 8.0, minimum=0.0),
                min_good_throughput_uph=_float_arg(args, "min_good_throughput_uph", 80.0, minimum=0.0),
                max_defect_rate=_float_arg(args, "max_defect_rate_pct", 100.0, minimum=0.0, maximum=100.0) / 100.0,
                annual_volume_units=_int_arg(args, "annual_volume_units", 200_000, minimum=1),
                effectiveness=_float_arg(args, "effectiveness", 1.0, minimum=0.0, maximum=1.0),
                demand_multiplier=_float_arg(args, "demand_multiplier", 1.0, minimum=0.5, maximum=1.75),
                min_evidence_score=_float_arg(args, "min_evidence_score", 25.0, minimum=0.0, maximum=100.0),
            )
        if name == "get_active_investigation_plan":
            return build_active_investigation_overview(self.records, self.activation_unit)
        if name == "get_experiment_design":
            return build_experiment_design(self.records, self.activation_unit)
        if name == "get_causal_gate":
            inv = self._investigation()
            return inv["causality_gate"]
        raise ValueError(f"Unknown engineering tool: {name}")
