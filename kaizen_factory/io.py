from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .models import SimulationResult


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def export_result(result: SimulationResult, root: str | Path) -> dict[str, str]:
    root_path = Path(root)
    run_dir = root_path / result.run_id
    sealed_dir = run_dir / ".sealed"
    sealed_dir.mkdir(parents=True, exist_ok=True)

    records_path = run_dir / "production_records.csv"
    metadata_path = run_dir / "run_metadata.json"
    latent_path = sealed_dir / "latent_records.csv"
    truth_path = sealed_dir / "ground_truth.json"

    _write_csv(records_path, result.records)
    _write_csv(latent_path, result.latent_records)

    metadata = result.public_metadata()
    metadata["public_summary"] = result.public_summary
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    truth_path.write_text(json.dumps(result.ground_truth, indent=2), encoding="utf-8")
    return {
        "run_dir": str(run_dir),
        "records": str(records_path),
        "metadata": str(metadata_path),
        "sealed_truth": str(truth_path),
        "sealed_latent_records": str(latent_path),
    }


def read_records(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))
