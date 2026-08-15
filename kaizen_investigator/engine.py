from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np
import pandas as pd
from scipy import stats

from .models import build_adjusted_models
from .statistics import (
    TestResult,
    bounded_effect,
    did_continuous,
    mann_whitney,
    pearson,
    proportion_test,
    significance_strength,
    welch,
)

ADHESIVE_LSL = {"A": 5.4, "B": 5.7, "C": 6.0}


@dataclass
class Hypothesis:
    code: str
    title: str
    mechanism_class: str
    target: str
    score: float
    summary: str
    primary: TestResult
    corroborating: list[TestResult]
    contradictory: list[str]
    assumptions: list[str]
    attribution: dict[str, Any] = field(default_factory=dict)

    def status(self) -> str:
        if self.score >= 80:
            return "STRONG_SUSPECT"
        if self.score >= 60:
            return "SUPPORTED_ASSOCIATION"
        if self.score >= 40:
            return "WEAK_SIGNAL"
        return "LOW_SUPPORT"

    def to_dict(self, rank: int) -> dict[str, Any]:
        return {
            "rank": rank,
            "code": self.code,
            "title": self.title,
            "mechanism_class": self.mechanism_class,
            "target": self.target,
            "evidence_score": round(float(self.score), 2),
            "status": self.status(),
            "summary": self.summary,
            "primary_test": self.primary.to_dict(),
            "corroborating_tests": [x.to_dict() for x in self.corroborating],
            "contradictory_evidence": self.contradictory,
            "assumptions": self.assumptions,
            "causal_status": "NOT_CONFIRMED",
            "attribution": self.attribution,
        }


def _frame(records: list[dict[str, Any]], activation_unit: int) -> pd.DataFrame:
    if not records:
        raise ValueError("Investigator requires observable production records")
    df = pd.DataFrame.from_records(records).copy()
    df.loc[:, "post"] = (df["unit_index"] >= activation_unit).astype(int)
    df.loc[:, "progress"] = np.where(
        df["post"].eq(1),
        (df["unit_index"] - activation_unit) / max(1, len(df) - activation_unit - 1),
        0.0,
    )
    df.loc[:, "torque_error_nm"] = df["torque_measured_nm"] - df["torque_target_nm"]
    df.loc[:, "abs_torque_error_nm"] = df["torque_error_nm"].abs()
    df.loc[:, "adhesive_lsl"] = df["product_variant"].map(ADHESIVE_LSL).astype(float)
    df.loc[:, "adhesive_margin_mpa"] = df["adhesive_strength_measured_mpa"] - df["adhesive_lsl"]
    df.loc[:, "transition"] = df["product_variant"].ne(df["product_variant"].shift(1)).astype(int)
    if len(df):
        df.loc[df.index[0], "transition"] = 0
    return df


def _sub(df: pd.DataFrame, post: int, col: str, value: Any, outcome: str, *, equal: bool = True) -> np.ndarray:
    mask = df["post"].eq(post)
    mask &= df[col].eq(value) if equal else df[col].ne(value)
    return df.loc[mask, outcome].astype(float).to_numpy()


def _did_best_level(df: pd.DataFrame, factor: str, outcome: str) -> tuple[Any, TestResult]:
    """Return the level with the largest absolute DID contrast.

    This is suitable for screening *whether* a factor family carries a signal, but
    not necessarily for assigning the affected asset. With a two-level factor, a
    shift on M2 creates an equal-and-opposite DID coefficient for M1. Therefore
    asset attribution must additionally inspect each level's own pre/post movement.
    """
    best: tuple[Any, TestResult] | None = None
    for level in sorted(df[factor].dropna().unique().tolist(), key=str):
        t = did_continuous(
            _sub(df, 0, factor, level, outcome),
            _sub(df, 0, factor, level, outcome, equal=False),
            _sub(df, 1, factor, level, outcome),
            _sub(df, 1, factor, level, outcome, equal=False),
            label=f"{factor}={level} × post contrast on {outcome}",
        )
        if best is None or abs(t.effect or 0.0) > abs(best[1].effect or 0.0):
            best = (level, t)
    if best is None:
        raise ValueError(f"No levels for {factor}")
    return best


def _did_attributed_level(df: pd.DataFrame, factor: str, outcome: str) -> tuple[Any, TestResult, dict[str, Any]]:
    """Attribute a DID family signal to the level that actually moved.

    A two-level DID is antisymmetric: if M2 rises relative to M1, the M1-vs-M2
    contrast is equally large and negative. Selecting only by ``abs(DID)`` can
    therefore name the unaffected complement. We rank each candidate using both
    the differential contrast and that candidate's *own observed pre/post change*.

    This uses observable records only and does not consume scenario/latent truth.
    """
    candidates: list[tuple[float, float, float, str, Any, TestResult, dict[str, Any]]] = []
    for level in sorted(df[factor].dropna().unique().tolist(), key=str):
        pre_target = _sub(df, 0, factor, level, outcome)
        post_target = _sub(df, 1, factor, level, outcome)
        t = did_continuous(
            pre_target,
            _sub(df, 0, factor, level, outcome, equal=False),
            post_target,
            _sub(df, 1, factor, level, outcome, equal=False),
            label=f"{factor}={level} × post contrast on {outcome}",
        )
        pre_mean = float(np.mean(pre_target)) if len(pre_target) else float('nan')
        post_mean = float(np.mean(post_target)) if len(post_target) else float('nan')
        own_change = post_mean - pre_mean if math.isfinite(pre_mean) and math.isfinite(post_mean) else 0.0
        did_effect = float(t.effect or 0.0)
        # Primary key: a strong differential signal *and* meaningful movement in
        # the candidate itself. This breaks equal-and-opposite two-level DID ties.
        attribution_strength = abs(did_effect) * abs(own_change)
        info = {
            "target": str(level),
            "target_type": factor,
            "factor": factor,
            "outcome": outcome,
            "interaction_partner": None,
            "pre_mean": pre_mean if math.isfinite(pre_mean) else None,
            "post_mean": post_mean if math.isfinite(post_mean) else None,
            "observed_change": own_change,
            "direction": "INCREASE" if own_change > 0 else "DECREASE" if own_change < 0 else "NO_CHANGE",
            "selection_basis": "DID magnitude × target level's own observed pre/post movement",
        }
        candidates.append((attribution_strength, abs(own_change), abs(did_effect), str(level), level, t, info))
    if not candidates:
        raise ValueError(f"No levels for {factor}")
    candidates.sort(key=lambda x: (x[0], x[1], x[2], x[3]), reverse=True)
    _, _, _, _, level, test, info = candidates[0]
    return level, test, info


def _trend_for_level(df: pd.DataFrame, factor: str, level: Any, outcome: str) -> TestResult:
    part = df[(df["post"] == 1) & (df[factor] == level)]
    return pearson(part["progress"], part[outcome], label=f"Post-incident time trend for {factor}={level} on {outcome}")


def _score(primary: TestResult, corroborating: list[TestResult], *, effect_ref: float = 0.8, bonus: float = 0.0) -> float:
    pe = bounded_effect(primary.effect, effect_ref)
    ps = significance_strength(primary.p_value)
    corr = 0.0
    if corroborating:
        corr = max(
            0.55 * bounded_effect(t.effect, effect_ref) + 0.45 * significance_strength(t.p_value)
            for t in corroborating
        )
    return float(min(100.0, 52.0 * pe + 24.0 * ps + 20.0 * corr + bonus))


def _machine_bias(df: pd.DataFrame) -> Hypothesis:
    level, primary, attribution = _did_attributed_level(df, "machine_id", "torque_error_nm")
    trend = _trend_for_level(df, "machine_id", level, "torque_error_nm")
    post = df[df.post == 1]
    target = post[post.machine_id == level]
    other = post[post.machine_id != level]
    prop = proportion_test(
        int((target.torque_error_nm > 1.35).sum()), len(target),
        int((other.torque_error_nm > 1.35).sum()), len(other),
        label=f"High-side torque rejects: {level} versus other machines (post)",
    )
    score = _score(primary, [trend, prop], effect_ref=0.75)
    return Hypothesis(
        "MACHINE_TORQUE_BIAS",
        f"Machine/tool bias centered on {level}",
        "process_equipment_bias",
        str(level),
        score,
        f"{level} shows the strongest pre/post differential shift in measured torque error among machines.",
        primary,
        [trend, prop],
        ["Machine assignment is partly confounded by product mix; the DID contrast reduces but does not eliminate that risk."],
        ["Measured torque is a valid proxy for the fastening process after accounting for the separate gage hypothesis."],
        attribution=attribution,
    )


def _gage_drift(df: pd.DataFrame) -> Hypothesis:
    level, primary, attribution = _did_attributed_level(df, "gage_id", "torque_error_nm")
    trend = _trend_for_level(df, "gage_id", level, "torque_error_nm")
    post = df[df.post == 1]
    target = post[post.gage_id == level]
    other = post[post.gage_id != level]
    defect = proportion_test(
        int(target.observed_defect.sum()), len(target), int(other.observed_defect.sum()), len(other),
        label=f"Observed defect rate: {level} versus other gages (post)",
    )
    score = _score(primary, [trend, defect], effect_ref=0.75)
    return Hypothesis(
        "GAGE_MEASUREMENT_DRIFT",
        f"Measurement-system drift centered on {level}",
        "measurement_system_bias",
        str(level),
        score,
        f"{level} shows the strongest differential pre/post shift in measured torque error among inspection gages.",
        primary,
        [trend, defect],
        ["A real process shift can also appear in measured data; machine and fixture hypotheses are evaluated separately."],
        ["Gage assignment remains sufficiently mixed across the process to support comparison."],
        attribution=attribution,
    )


def _fixture_temperature(df: pd.DataFrame) -> Hypothesis:
    best = None
    for fixture in sorted(df.fixture_id.unique()):
        primary = did_continuous(
            _sub(df, 0, "fixture_id", fixture, "abs_torque_error_nm"),
            _sub(df, 0, "fixture_id", fixture, "abs_torque_error_nm", equal=False),
            _sub(df, 1, "fixture_id", fixture, "abs_torque_error_nm"),
            _sub(df, 1, "fixture_id", fixture, "abs_torque_error_nm", equal=False),
            label=f"{fixture} × post contrast on absolute torque error",
        )
        post_target = df[(df.post == 1) & (df.fixture_id == fixture)]
        temp = pearson(post_target.ambient_temp_c, post_target.torque_error_nm, label=f"Temperature/torque association within {fixture} post-incident")
        align = did_continuous(
            _sub(df, 0, "fixture_id", fixture, "alignment_measured_mm"),
            _sub(df, 0, "fixture_id", fixture, "alignment_measured_mm", equal=False),
            _sub(df, 1, "fixture_id", fixture, "alignment_measured_mm"),
            _sub(df, 1, "fixture_id", fixture, "alignment_measured_mm", equal=False),
            label=f"{fixture} × post contrast on measured alignment",
        )
        score = _score(primary, [temp, align], effect_ref=0.65)
        # A true interaction should have both fixture-local shift and at least some environmental/alignment corroboration.
        score *= 0.72 + 0.28 * max(bounded_effect(temp.effect, 0.35), bounded_effect(align.effect, 0.55))
        item = (score, fixture, primary, temp, align)
        if best is None or item[0] > best[0]:
            best = item
    assert best is not None
    score, fixture, primary, temp, align = best
    pre_fixture = df[(df.post == 0) & (df.fixture_id == fixture)].abs_torque_error_nm
    post_fixture = df[(df.post == 1) & (df.fixture_id == fixture)].abs_torque_error_nm
    fixture_pre = float(pre_fixture.mean()) if len(pre_fixture) else None
    fixture_post = float(post_fixture.mean()) if len(post_fixture) else None
    fixture_change = (fixture_post - fixture_pre) if fixture_pre is not None and fixture_post is not None else None
    attribution = {
        "target": str(fixture),
        "target_type": "fixture_id",
        "outcome": "abs_torque_error_nm",
        "pre_mean": fixture_pre,
        "post_mean": fixture_post,
        "observed_change": fixture_change,
        "direction": "INCREASE" if (fixture_change or 0) > 0 else "DECREASE" if (fixture_change or 0) < 0 else "NO_CHANGE",
        "interaction_partner": "ambient_temp_c",
        "selection_basis": "highest fixture-specific evidence score combining DID, temperature association and alignment corroboration",
    }
    return Hypothesis(
        "FIXTURE_ENVIRONMENT_INTERACTION",
        f"Fixture {fixture} instability with environmental interaction",
        "fixture_environment_interaction",
        str(fixture),
        score,
        f"{fixture} has the strongest post-incident change in torque variability, with temperature/alignment checked as corroborating mechanisms.",
        primary,
        [temp, align],
        ["Operator assignment is not random; a fixture effect can be confounded by who runs that fixture."],
        ["Ambient temperature is measured accurately enough to detect an interaction signal."],
        attribution=attribution,
    )


def _supplier_humidity(df: pd.DataFrame) -> Hypothesis:
    post = df[df.post == 1].copy()
    lot_stats = post.groupby("supplier_lot", observed=True).agg(
        n=("adhesive_margin_mpa", "size"),
        mean_margin=("adhesive_margin_mpa", "mean"),
    )
    eligible = lot_stats[lot_stats.n >= max(20, int(len(post) * 0.015))]
    if eligible.empty:
        eligible = lot_stats
    lot = str(eligible.mean_margin.idxmin())
    target = post[post.supplier_lot == lot]
    other = post[post.supplier_lot != lot]
    primary = welch(target.adhesive_margin_mpa, other.adhesive_margin_mpa, label=f"Adhesive margin for lot {lot} versus other post-incident lots")
    humidity = pearson(target.humidity_pct, target.adhesive_margin_mpa, label=f"Humidity/adhesive association within suspect lot {lot}")
    supplier = str(target.supplier.mode().iloc[0]) if len(target) else "unknown"
    supplier_did = did_continuous(
        _sub(df, 0, "supplier", supplier, "adhesive_margin_mpa"),
        _sub(df, 0, "supplier", supplier, "adhesive_margin_mpa", equal=False),
        _sub(df, 1, "supplier", supplier, "adhesive_margin_mpa"),
        _sub(df, 1, "supplier", supplier, "adhesive_margin_mpa", equal=False),
        label=f"Supplier {supplier} × post contrast on adhesive margin",
    )
    # Negative primary effect is expected; magnitude matters. Strong lot localization gets a small bonus.
    score = _score(primary, [humidity, supplier_did], effect_ref=0.9, bonus=min(8.0, len(target) / max(1, len(post)) * 20.0))
    target_mean = float(target.adhesive_margin_mpa.mean()) if len(target) else None
    other_mean = float(other.adhesive_margin_mpa.mean()) if len(other) else None
    attribution = {
        "target": lot,
        "target_type": "supplier_lot",
        "supplier": supplier,
        "outcome": "adhesive_margin_mpa",
        "target_post_mean": target_mean,
        "other_post_mean": other_mean,
        "observed_change": (target_mean - other_mean) if target_mean is not None and other_mean is not None else None,
        "direction": "DECREASE",
        "interaction_partner": "humidity_pct",
        "selection_basis": "lowest sufficiently represented post-incident product-adjusted adhesive margin with humidity/supplier corroboration",
    }
    return Hypothesis(
        "SUPPLIER_HUMIDITY_INTERACTION",
        f"Material-lot effect centered on {lot} with humidity interaction",
        "supplier_material_environment_interaction",
        lot,
        score,
        f"{lot} has the lowest post-incident adhesive margin among sufficiently represented lots; humidity and supplier-level contrasts are checked separately.",
        primary,
        [humidity, supplier_did],
        ["Lot exposure is time-structured, so temporal drift can mimic a lot effect."],
        ["Product-specific adhesive lower limits are correctly represented by the observed product variant."],
        attribution=attribution,
    )


def _changeover(df: pd.DataFrame) -> Hypothesis:
    primary = did_continuous(
        df[(df.post == 0) & (df.transition == 1)].calibration_s,
        df[(df.post == 0) & (df.transition == 0)].calibration_s,
        df[(df.post == 1) & (df.transition == 1)].calibration_s,
        df[(df.post == 1) & (df.transition == 0)].calibration_s,
        label="Product-transition × post contrast on calibration time",
    )
    post_trans = df[(df.post == 1) & (df.transition == 1)]
    post_same = df[(df.post == 1) & (df.transition == 0)]
    mw = mann_whitney(post_trans.calibration_s, post_same.calibration_s, label="Post calibration time on transitions versus same-product runs")
    queue = welch(df[df.post == 1].queue_wait_s, df[df.post == 0].queue_wait_s, label="Post versus pre queue wait")
    score = _score(primary, [mw, queue], effect_ref=0.9)
    pre_trans_mean = float(df[(df.post == 0) & (df.transition == 1)].calibration_s.mean())
    post_trans_mean = float(post_trans.calibration_s.mean()) if len(post_trans) else None
    attribution = {
        "target": "Calibration product transitions",
        "target_type": "sequence_condition",
        "outcome": "calibration_s",
        "pre_mean": pre_trans_mean,
        "post_mean": post_trans_mean,
        "observed_change": (post_trans_mean - pre_trans_mean) if post_trans_mean is not None else None,
        "direction": "INCREASE",
        "interaction_partner": "product_transition",
        "selection_basis": "transition × post DID with queue/service-time corroboration",
    }
    return Hypothesis(
        "SEQUENCE_CHANGEOVER_LOSS",
        "Sequence-dependent changeover loss at calibration",
        "sequence_dependent_capacity_loss",
        "Calibration product transitions",
        score,
        "Calibration time changes disproportionately on product transitions, which is the observable signature of a changeover-specific loss.",
        primary,
        [mw, queue],
        ["Product variants have different normal calibration times; the DID contrast is used to isolate a post-incident transition penalty."],
        ["The record order represents the actual product sequence presented to calibration."],
        attribution=attribution,
    )


def _microstops(df: pd.DataFrame, changeover_score: float) -> Hypothesis:
    pre = df[df.post == 0]
    post = df[df.post == 1]
    threshold = float(pre.calibration_s.quantile(0.99))
    pre_tail = int((pre.calibration_s > threshold).sum())
    post_tail = int((post.calibration_s > threshold).sum())
    primary = proportion_test(post_tail, len(post), pre_tail, len(pre), label=f"Calibration tail rate above pre-incident P99 ({threshold:.2f}s): post versus pre")
    p95_shift = welch(post.calibration_s, pre.calibration_s, label="Post versus pre calibration service time")
    queue = mann_whitney(post.queue_wait_s, pre.queue_wait_s, label="Post versus pre calibration queue wait")
    raw = _score(primary, [p95_shift, queue], effect_ref=0.22)
    # If a transition-specific model is overwhelmingly stronger, interpret the delay as changeover loss rather than generic micro-stops.
    penalty = min(32.0, max(0.0, changeover_score - 55.0) * 0.70)
    score = max(0.0, raw - penalty)
    attribution = {
        "target": "Calibration",
        "target_type": "station",
        "outcome": "calibration_s_tail_rate",
        "pre_tail_rate": pre_tail / max(1, len(pre)),
        "post_tail_rate": post_tail / max(1, len(post)),
        "observed_change": post_tail / max(1, len(post)) - pre_tail / max(1, len(pre)),
        "direction": "INCREASE",
        "interaction_partner": None,
        "selection_basis": "post-vs-pre expansion of the calibration upper tail, penalized when transition-specific loss explains the same signal",
    }
    return Hypothesis(
        "CALIBRATION_INTERMITTENT_LOSS",
        "Intermittent calibration capacity loss / micro-stop pattern",
        "intermittent_capacity_loss",
        "Calibration",
        score,
        f"The post-incident calibration-time tail above the pre P99 expands from {pre_tail}/{len(pre)} to {post_tail}/{len(post)} observations.",
        primary,
        [p95_shift, queue],
        ["A sequence-dependent changeover problem can also inflate the upper tail; that competing hypothesis is explicitly scored."],
        ["Extreme calibration durations are genuine service-time observations rather than logging artifacts."],
        attribution=attribution,
    )


def _nuisance_checks(df: pd.DataFrame) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for factor in ("operator_id", "shift", "product_variant"):
        try:
            level, test = _did_best_level(df, factor, "torque_error_nm")
        except Exception:
            continue
        checks.append({
            "factor": factor,
            "level": str(level),
            "test": test.to_dict(),
            "interpretation": "Potential confounder only; not promoted to a process cause without mechanism-specific evidence.",
        })
    return checks


def _global_tests(df: pd.DataFrame) -> list[TestResult]:
    pre, post = df[df.post == 0], df[df.post == 1]
    tests = [
        welch(post.torque_error_nm, pre.torque_error_nm, label="Post versus pre measured torque error"),
        welch(post.adhesive_margin_mpa, pre.adhesive_margin_mpa, label="Post versus pre adhesive margin"),
        mann_whitney(post.calibration_s, pre.calibration_s, label="Post versus pre calibration service time"),
        mann_whitney(post.queue_wait_s, pre.queue_wait_s, label="Post versus pre queue wait"),
        proportion_test(int(post.observed_defect.sum()), len(post), int(pre.observed_defect.sum()), len(pre), label="Post versus pre observed defect rate"),
    ]
    return tests


def _gate(top: Hypothesis, hypotheses: list[Hypothesis], adjusted_models: dict[str, Any]) -> dict[str, Any]:
    primary_sig = top.primary.p_value is not None and top.primary.p_value < 0.05
    meaningful = bounded_effect(top.primary.effect, 0.5) >= 0.5
    corroborated = any((t.p_value is not None and t.p_value < 0.05 and bounded_effect(t.effect, 0.3) >= 0.25) for t in top.corroborating)
    adjusted_ok = adjusted_models.get("status") in {"FIT", "PARTIAL"} and adjusted_models.get("models_fit", 0) >= 4
    levels = [
        {"level": 0, "name": "Observed process change", "passed": True, "meaning": "A measurable post-incident change exists in the observed process record."},
        {"level": 1, "name": "Association", "passed": bool(primary_sig), "meaning": "The leading factor is statistically associated with the changed outcome."},
        {"level": 2, "name": "Meaningful effect", "passed": bool(primary_sig and meaningful), "meaning": "The association is not only statistically detectable; its standardized effect is material."},
        {"level": 3, "name": "Adjusted / interaction evidence", "passed": bool(primary_sig and meaningful and corroborated and adjusted_ok), "meaning": "A second observable mechanism signal exists and adjusted regression/ANOVA models are available to challenge obvious confounding."},
        {"level": 4, "name": "Competing explanations reviewed", "passed": len(hypotheses) >= 3, "meaning": "Alternative equipment, measurement, material and flow explanations were scored in parallel."},
        {"level": 5, "name": "Intervention / DOE confirmation", "passed": False, "meaning": "Locked in the observational statistical core. V0.9 may unlock a separate Level-5 gate only after an authorized predeclared controlled synthetic DOE."},
    ]
    highest = max((x["level"] for x in levels if x["passed"]), default=0)
    return {
        "highest_passed_level": highest,
        "causal_verdict": "OBSERVATIONAL_SUSPECT_ONLY",
        "levels": levels,
        "policy": "No observational hypothesis may be labeled root cause or causal confirmation without intervention/DOE evidence. V0.9 controlled DOE confirmation is tracked separately from this statistical core.",
    }



def _test_router() -> list[dict[str, Any]]:
    return [
        {"mechanism_class": "process_equipment_bias", "primary_route": "machine × post difference-in-differences on torque error", "corroboration": ["post time trend", "high-side reject risk difference", "adjusted torque OLS/ANOVA"]},
        {"mechanism_class": "measurement_system_bias", "primary_route": "gage × post difference-in-differences on torque error", "corroboration": ["post time trend", "gage-stratified defect risk", "adjusted torque OLS/ANOVA"]},
        {"mechanism_class": "fixture_environment_interaction", "primary_route": "fixture × post contrast on absolute torque error", "corroboration": ["temperature correlation within fixture", "alignment shift", "adjusted torque OLS/ANOVA"]},
        {"mechanism_class": "supplier_material_environment_interaction", "primary_route": "worst represented post lot vs other lots on product-adjusted adhesive margin", "corroboration": ["humidity association", "supplier × post DID", "adjusted adhesive OLS"]},
        {"mechanism_class": "sequence_dependent_capacity_loss", "primary_route": "product transition × post DID on calibration time", "corroboration": ["post transition Mann-Whitney", "queue-wait shift", "transition interaction OLS"]},
        {"mechanism_class": "intermittent_capacity_loss", "primary_route": "post vs pre calibration tail-rate test above pre P99", "corroboration": ["calibration-time shift", "queue-wait shift", "penalty when transition model explains the tail"]},
    ]

def build_investigation_overview(records: list[dict[str, Any]], activation_unit: int) -> dict[str, Any]:
    """Rank observable-data hypotheses without access to latent ground truth.

    The only inputs are production records and the incident boundary. There is
    intentionally no scenario code, latent record, or revealed truth argument.
    """
    df = _frame(records, activation_unit)
    adjusted_models = build_adjusted_models(df)

    changeover = _changeover(df)
    hypotheses = [
        _machine_bias(df),
        _gage_drift(df),
        _fixture_temperature(df),
        _supplier_humidity(df),
        changeover,
        _microstops(df, changeover.score),
    ]
    hypotheses.sort(key=lambda h: h.score, reverse=True)
    top = hypotheses[0]

    global_tests = _global_tests(df)
    evidence_ledger: list[dict[str, Any]] = []
    eid = 1
    for rank, h in enumerate(hypotheses, start=1):
        for role, test in [("PRIMARY", h.primary), *[("CORROBORATING", t) for t in h.corroborating]]:
            evidence_ledger.append({
                "evidence_id": f"EVD-{eid:04d}",
                "hypothesis_code": h.code,
                "hypothesis_rank": rank,
                "role": role,
                **test.to_dict(),
            })
            eid += 1

    score_gap = top.score - hypotheses[1].score if len(hypotheses) > 1 else top.score
    ambiguity = "LOW" if score_gap >= 20 and top.score >= 75 else "MEDIUM" if score_gap >= 8 else "HIGH"

    return {
        "evidence_state": {
            "analyze_core": "IMPLEMENTED_AND_TESTED",
            "causal_confirmation": "LOCKED",
            "ai_reasoning": "EXTERNAL_GEMINI_COPILOT_AVAILABLE_NOT_IN_STATISTICAL_CORE",
        },
        "methodology": {
            "inputs": "observable production records + activation boundary only",
            "scenario_code_available": False,
            "latent_ground_truth_available": False,
            "families_compared": [h.mechanism_class for h in hypotheses],
            "multiple_comparison_note": "Scores are a screening/ranking device, not family-wise-error-controlled causal proof.",
            "evidence_score_note": "0-100 evidence score is a deterministic ranking index combining effect magnitude, significance and corroboration; it is NOT a probability.",
            "confidence_interval_note": "Where reported, 95% confidence intervals describe the sampled statistical contrast or association; they are not causal intervals.",
        },
        "test_router": _test_router(),
        "adjusted_models": adjusted_models,
        "top_suspect": hypotheses[0].to_dict(1),
        "ranked_hypotheses": [h.to_dict(i) for i, h in enumerate(hypotheses, start=1)],
        "ambiguity": {
            "level": ambiguity,
            "top_to_second_score_gap": round(float(score_gap), 2),
            "message": "High ambiguity means the observable evidence does not clearly separate the leading explanations." if ambiguity == "HIGH" else "The leading explanation is separated from alternatives, but remains observational until an intervention/DOE test.",
        },
        "causality_gate": _gate(top, hypotheses, adjusted_models),
        "global_pre_post_tests": [t.to_dict() for t in global_tests],
        "confounder_checks": _nuisance_checks(df),
        "evidence_ledger": evidence_ledger,
        "investigation_note": "The Statistical Investigator identifies supported suspects and contradictory evidence from observable data only. It does not reveal or consume the simulator's hidden causal answer; V0.9 controlled DOE execution is a separate authorized test layer.",
    }
