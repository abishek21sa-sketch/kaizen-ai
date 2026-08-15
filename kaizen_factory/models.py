from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class FactoryConfig:
    seed: int = 42
    units: int = 2500
    start_time: str = "2026-08-03T06:00:00"
    activation_fraction: float = 0.42
    line_name: str = "Actuator Assembly Line A"

    def validate(self) -> None:
        if self.units < 100:
            raise ValueError("units must be at least 100")
        if self.units > 250_000:
            raise ValueError("units must not exceed 250,000 for demo runs")
        if not 0.05 <= self.activation_fraction <= 0.95:
            raise ValueError("activation_fraction must be between 0.05 and 0.95")
        datetime.fromisoformat(self.start_time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FaultScenario:
    code: str
    label: str
    public_symptom: str
    affected_step: str
    root_cause: str
    mechanism: str
    causal_graph: list[str]
    confounders: list[str] = field(default_factory=list)
    expected_signals: list[str] = field(default_factory=list)

    def public_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "label": self.label,
            "public_symptom": self.public_symptom,
            "affected_step": self.affected_step,
        }

    def truth_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SimulationResult:
    run_id: str
    config: FactoryConfig
    scenario_code: str
    activation_unit: int
    public_summary: dict[str, Any]
    records: list[dict[str, Any]]
    latent_records: list[dict[str, Any]]
    ground_truth: dict[str, Any]
    source_mode: str = "DEMO"
    source_metadata: dict[str, Any] = field(default_factory=dict)

    def public_metadata(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "line_name": self.config.line_name,
            "seed": self.config.seed,
            "units": self.config.units,
            "activation_unit": self.activation_unit,
            "public_summary": self.public_summary,
            "source_mode": self.source_mode,
            "source_metadata": self.source_metadata,
        }

    def internal_metadata(self) -> dict[str, Any]:
        data = self.public_metadata()
        data["scenario_code"] = self.scenario_code
        return data
