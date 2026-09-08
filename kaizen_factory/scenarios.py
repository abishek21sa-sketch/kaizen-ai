from __future__ import annotations

from .models import FaultScenario


FAULT_CATALOG: dict[str, FaultScenario] = {
    "fixture_wear_temp": FaultScenario(
        code="fixture_wear_temp",
        label="Torque CTQ instability",
        public_symptom="Torque variation rises and end-of-line failures begin clustering.",
        affected_step="Torque Fastening",
        root_cause="Progressive wear on fixture F4, amplified by elevated ambient temperature",
        mechanism=(
            "Fixture F4 wear increases shaft misalignment. At elevated ambient temperature, "
            "the worn fixture becomes more sensitive to thermal expansion, amplifying torque error."
        ),
        causal_graph=[
            "fixture_F4_age",
            "alignment_error",
            "temperature_interaction",
            "torque_error",
            "functional_failure",
        ],
        confounders=["operator O3 is scheduled more often on F4", "product C has a higher torque target"],
        expected_signals=["variance increase", "F4 concentration", "temperature interaction", "Cpk deterioration"],
    ),
    "supplier_resin_shift": FaultScenario(
        code="supplier_resin_shift",
        label="Adhesive cure failures",
        public_symptom="Bond-strength failures rise after a supplier lot transition.",
        affected_step="Adhesive Dispense",
        root_cause="Low-viscosity resin lot from supplier S2 interacting with high humidity",
        mechanism=(
            "A shifted S2 resin lot reduces cured bond strength. High humidity further lowers cure performance, "
            "creating an interaction rather than a supplier-only effect."
        ),
        causal_graph=["supplier_S2_shifted_lot", "humidity_interaction", "bond_strength_loss", "cure_failure"],
        confounders=["S2 lots are used more often on night shift", "product B uses more adhesive"],
        expected_signals=["lot cluster", "humidity interaction", "bond-strength mean shift"],
    ),
    "tool_calibration_drift": FaultScenario(
        code="tool_calibration_drift",
        label="Fastening bias drift",
        public_symptom="Measured torque gradually drifts high and high-side fastening rejects begin clustering on one machine.",
        affected_step="Torque Fastening",
        root_cause="Calibration bias developing in torque tool M2",
        mechanism="Tool M2 develops a progressive positive torque bias after the incident activation point.",
        causal_graph=["M2_calibration_bias", "torque_mean_shift", "high_torque_defect"],
        confounders=["M2 runs more product C", "shift 2 has a slightly faster work pace"],
        expected_signals=["M2-specific mean shift", "time trend", "high-side defects"],
    ),
    "gage_measurement_drift": FaultScenario(
        code="gage_measurement_drift",
        label="Inspection false rejects",
        public_symptom="Inspection rejects increase even though downstream functional performance remains stable.",
        affected_step="Final Inspection",
        root_cause="Measurement gage G2 zero drift; the process itself remains physically stable",
        mechanism=(
            "Gage G2 develops a positive measurement offset. Actual torque remains in control, but measured torque "
            "crosses the inspection limit, producing false rework."
        ),
        causal_graph=["G2_zero_drift", "measurement_bias", "false_reject", "rework_cost"],
        confounders=["G2 is used more often on shift 3"],
        expected_signals=["measured-vs-actual divergence", "G2 concentration", "stable functional failures"],
    ),
    "calibration_microstops": FaultScenario(
        code="calibration_microstops",
        label="Lead-time and WIP surge",
        public_symptom="WIP and lead time increase without a corresponding quality loss.",
        affected_step="Calibration",
        root_cause="Intermittent sensor handshake micro-stoppages at calibration station C1",
        mechanism=(
            "Random 20-55 second sensor handshake delays reduce effective calibration capacity. "
            "The resulting utilization increase propagates upstream as queueing and WIP."
        ),
        causal_graph=["C1_microstop", "capacity_loss", "queue_growth", "WIP_growth", "lead_time_growth"],
        confounders=["demand mix shifts toward product C, which has a longer calibration cycle"],
        expected_signals=["calibration cycle-time tail", "queue increase", "quality stable"],
    ),
    "changeover_deterioration": FaultScenario(
        code="changeover_deterioration",
        label="Changeover performance loss",
        public_symptom="Schedule adherence deteriorates as product-mix changes become more expensive.",
        affected_step="Calibration",
        root_cause="Changeover standard work deterioration after fixture-kit reorganization",
        mechanism=(
            "Variant transitions require additional search/setup time after the fixture-kit layout changes. "
            "The loss only appears on product transitions, creating a sequence-dependent capacity problem."
        ),
        causal_graph=["kit_layout_change", "transition_setup_delay", "capacity_loss", "schedule_lateness"],
        confounders=["product mix becomes more variable later in the run"],
        expected_signals=["transition-only delay", "setup-time shift", "sequence dependence"],
    ),
}


def get_scenario(code: str) -> FaultScenario:
    try:
        return FAULT_CATALOG[code]
    except KeyError as exc:
        raise ValueError(f"Unknown fault scenario: {code}") from exc
