from __future__ import annotations

from typing import Any

from .capability import capability_suite
from .data_quality import data_quality_report
from .define import build_define_package
from .msa import gage_stratification, generate_baseline_msa_study
from .pareto import pareto_and_copq
from .spc import spc_suite


def build_quality_overview(records: list[dict[str, Any]], activation_unit: int, *, line_name: str, seed: int) -> dict[str, Any]:
    return {
        "define": build_define_package(records, activation_unit, line_name),
        "data_quality": data_quality_report(records),
        "pareto_copq": pareto_and_copq(records),
        "capability": capability_suite(records, activation_unit),
        "spc": spc_suite(records, activation_unit),
        "msa": {
            "gage_stratification": gage_stratification(records),
            "crossed_gage_rr": generate_baseline_msa_study(records, activation_unit, seed),
        },
        "evidence_state": {
            "define_measure_core": "IMPLEMENTED_AND_TESTED",
            "causal_claims": "NOT_PERMITTED_BEFORE_V0_4",
            "ground_truth_dependency": False,
        },
    }
