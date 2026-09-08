from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class ToolTraceEntry(BaseModel):
    tool: str
    arguments: dict = Field(default_factory=dict)
    result_summary: str


class GroundedAIResponse(BaseModel):
    mode: Literal["ASK", "RED_TEAM"] = "ASK"
    headline: str
    answer: str
    confidence_language: str
    causal_status: Literal["OBSERVATIONAL_ONLY", "INCONCLUSIVE", "NOT_CAUSALLY_CONFIRMED"] = "NOT_CAUSALLY_CONFIRMED"
    evidence_ids: list[str] = Field(
        default_factory=list,
        description="Only statistical evidence-ledger identifiers in literal EVD-#### form. Never place hypothesis, intervention, asset, or tool codes here.",
    )
    engineering_references: list[str] = Field(
        default_factory=list,
        description="Exact observable/registered KAIZEN references such as hypothesis/intervention codes, runtime assets (M2, G1, F4), supplier lots, stations or other identifiers returned by KAIZEN tools. These are not evidence citations.",
    )
    contradictory_evidence: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    recommended_next_actions: list[str] = Field(default_factory=list)


class AIExecutionResult(BaseModel):
    response: GroundedAIResponse
    tool_trace: list[ToolTraceEntry]
    provider: str
    model: str
    grounded: bool = True
    truth_dependency: bool = False
    causal_confirmation_unlocked: bool = False
