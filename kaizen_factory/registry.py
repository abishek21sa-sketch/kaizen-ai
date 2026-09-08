from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import SimulationResult


@dataclass
class StoredRun:
    result: SimulationResult
    revealed: bool = False


class RunRegistry:
    def __init__(self) -> None:
        self._runs: dict[str, StoredRun] = {}

    def put(self, result: SimulationResult) -> None:
        self._runs[result.run_id] = StoredRun(result=result)

    def get(self, run_id: str) -> StoredRun:
        try:
            return self._runs[run_id]
        except KeyError as exc:
            raise KeyError(f"Unknown run_id: {run_id}") from exc

    def reveal(self, run_id: str) -> dict[str, Any]:
        stored = self.get(run_id)
        stored.revealed = True
        return stored.result.ground_truth

    def list_public(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for run_id, stored in self._runs.items():
            meta = stored.result.public_metadata()
            meta["truth_revealed"] = stored.revealed
            items.append(meta)
        return items
