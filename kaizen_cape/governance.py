"""CAPE-Loop experiment-portfolio assurance certificate.

The certificate binds the observable-data fingerprint, allocation, resource envelope,
and causal firewall into one reviewable object. It authorizes no production change
and cannot unlock causal confirmation.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def observable_fingerprint(records: list[dict[str, Any]]) -> str:
    return hashlib.sha256(_canonical(records)).hexdigest()


def certify_cape_plan(
    *,
    run_id: str,
    records: list[dict[str, Any]],
    cape: dict[str, Any],
    source_mode: str,
    truth_revealed: bool,
    version: str,
    build_id: str,
) -> dict[str, Any]:
    limits = cape.get("resource_limits", {})
    use = cape.get("resource_use", {})
    firewall = cape.get("causal_firewall", {})
    checks = {
        "optimizer_optimal": cape.get("status") == "OPTIMAL",
        "budget_within_limit": float(use.get("budget_usd", 0.0)) <= float(limits.get("budget_usd", 0.0)) + 1e-9,
        "downtime_within_limit": float(use.get("downtime_hours", 0.0)) <= float(limits.get("max_downtime_hours", 0.0)) + 1e-9,
        "experiment_runs_within_limit": int(use.get("runs", 0)) <= int(limits.get("max_experiment_runs", 0)),
        "causal_firewall_locked": firewall.get("causal_confirmation_unlocked") is False,
        "observable_records_present": len(records) >= 100,
    }
    state = "EXPERIMENT_PORTFOLIO_REVIEW" if all(checks.values()) else "HOLD"
    core = {
        "certificate_type": "KAIZEN_CAPE_ASSURANCE_V1",
        "run_id": run_id,
        "version": version,
        "build_id": build_id,
        "decision_state": state,
        "source_mode": source_mode,
        "truth_revealed_at_certification": bool(truth_revealed),
        "observable_data_sha256": observable_fingerprint(records),
        "record_count": len(records),
        "allocation": cape.get("allocation", []),
        "objective_information_priority": cape.get("objective_information_priority"),
        "resource_use": use,
        "resource_limits": limits,
        "checks": checks,
        "causal_firewall": firewall,
        "approval_authority": "CONTINUOUS_IMPROVEMENT_ENGINEER",
        "experiment_execution_requires_human_authorization": True,
        "production_process_change_allowed": False,
        "claim_boundary": "CAPE allocates evidence-generation effort; it does not establish causality or authorize a production process change.",
    }
    digest = hashlib.sha256(_canonical(core)).hexdigest()
    return {**core, "certificate_sha256": digest, "generated_at_utc": datetime.now(timezone.utc).isoformat()}


def verify_cape_certificate(certificate: dict[str, Any]) -> dict[str, Any]:
    stored = certificate.get("certificate_sha256")
    core = {k: v for k, v in certificate.items() if k not in {"certificate_sha256", "generated_at_utc"}}
    expected = hashlib.sha256(_canonical(core)).hexdigest()
    return {"valid": bool(stored and stored == expected), "stored_sha256": stored, "expected_sha256": expected, "decision_state": certificate.get("decision_state")}
