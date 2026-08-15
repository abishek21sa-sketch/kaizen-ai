from __future__ import annotations

from pydantic import BaseModel, Field


class RunCreate(BaseModel):
    seed: int = Field(default=42, ge=0, le=2_147_483_647)
    units: int = Field(default=2500, ge=100, le=250_000)
    scenario: str = "random"
    activation_fraction: float = Field(default=0.42, ge=0.05, le=0.95)


class RunCreated(BaseModel):
    run_id: str
    units: int
    activation_unit: int
    symptom: str
    affected_step_hint: str
    truth_revealed: bool = False


class WhatIfRequest(BaseModel):
    intervention_code: str
    effectiveness: float = Field(default=1.0, ge=0.0, le=1.0)
    demand_multiplier: float = Field(default=1.0, ge=0.5, le=1.75)
    min_evidence_score: float = Field(default=25.0, ge=0.0, le=100.0)


class OptimizerRequest(BaseModel):
    budget_usd: float = Field(default=25_000.0, ge=0.0, le=10_000_000.0)
    max_downtime_hours: float = Field(default=8.0, ge=0.0, le=10_000.0)
    min_good_throughput_uph: float = Field(default=80.0, ge=0.0, le=1_000_000.0)
    max_defect_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    annual_volume_units: int = Field(default=200_000, ge=1, le=100_000_000)
    effectiveness: float = Field(default=1.0, ge=0.0, le=1.0)
    demand_multiplier: float = Field(default=1.0, ge=0.5, le=1.75)
    min_evidence_score: float = Field(default=25.0, ge=0.0, le=100.0)


class AIAskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=4000)
    mode: str = Field(default="ASK", pattern="^(ASK|RED_TEAM)$")

class ProbeRequest(BaseModel):
    probe_code: str


class HumanPredictionRequest(BaseModel):
    hypothesis_code: str


class ExperimentExecuteRequest(BaseModel):
    experiment_code: str
    authorized: bool = False

from typing import Any


class ExternalDataRequest(BaseModel):
    records: list[dict[str, Any]] = Field(min_length=100, max_length=250_000)
    activation_unit: int = Field(ge=1)
    line_name: str = Field(default="External Manufacturing Line", min_length=1, max_length=200)
    source_mode: str = Field(default="FILE", pattern="^(FILE|REPLAY)$")
    mapping: dict[str, str] = Field(default_factory=dict)


class LiveSessionCreateRequest(BaseModel):
    line_name: str = Field(default="Live Manufacturing Line", min_length=1, max_length=200)
    activation_unit: int | None = Field(default=None, ge=1)
    mapping: dict[str, str] = Field(default_factory=dict)


class LiveEventsRequest(BaseModel):
    records: list[dict[str, Any]] = Field(min_length=1, max_length=10_000)


class LiveFinalizeRequest(BaseModel):
    activation_unit: int | None = Field(default=None, ge=1)
