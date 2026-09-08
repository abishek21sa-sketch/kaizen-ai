from __future__ import annotations

import hashlib
import math
import statistics
from typing import Any

import numpy as np
from scipy import stats

from kaizen_arena.engine import EXPECTED_ATTRIBUTION
from kaizen_investigator import build_investigation_overview
from kaizen_simulation.engine import HYPOTHESIS_TO_INTERVENTION, INTERVENTION_CATALOG


PROBE_CATALOG: dict[str, dict[str, Any]] = {
    "MACHINE_TORQUE_BIAS": {
        "code": "PRODUCT_BALANCED_MACHINE_CHECK",
        "label": "Product-balanced machine contrast",
        "cost_usd": 180.0,
        "duration_hours": 0.5,
        "question": "Does the suspect machine still shift torque after balancing product mix?",
        "discrimination": ["MACHINE_TORQUE_BIAS", "FIXTURE_ENVIRONMENT_INTERACTION"],
    },
    "GAGE_MEASUREMENT_DRIFT": {
        "code": "CROSS_GAGE_REPEAT_CHECK",
        "label": "Cross-gage repeat check",
        "cost_usd": 120.0,
        "duration_hours": 0.4,
        "question": "Does the suspect gage preserve a measurement offset after stratification?",
        "discrimination": ["GAGE_MEASUREMENT_DRIFT", "MACHINE_TORQUE_BIAS"],
    },
    "FIXTURE_ENVIRONMENT_INTERACTION": {
        "code": "FIXTURE_THERMAL_STRATIFICATION",
        "label": "Fixture × temperature stratification",
        "cost_usd": 240.0,
        "duration_hours": 0.8,
        "question": "Does the suspect fixture become materially worse as ambient temperature rises?",
        "discrimination": ["FIXTURE_ENVIRONMENT_INTERACTION", "MACHINE_TORQUE_BIAS"],
    },
    "SUPPLIER_HUMIDITY_INTERACTION": {
        "code": "LOT_HUMIDITY_STRATIFICATION",
        "label": "Lot × humidity stratification",
        "cost_usd": 220.0,
        "duration_hours": 0.7,
        "question": "Does the suspect material lot lose adhesive margin disproportionately at high humidity?",
        "discrimination": ["SUPPLIER_HUMIDITY_INTERACTION", "FIXTURE_ENVIRONMENT_INTERACTION"],
    },
    "SEQUENCE_CHANGEOVER_LOSS": {
        "code": "MATCHED_CHANGEOVER_TIME_STUDY",
        "label": "Matched changeover time study",
        "cost_usd": 90.0,
        "duration_hours": 0.6,
        "question": "Is excess calibration time specifically concentrated on product transitions?",
        "discrimination": ["SEQUENCE_CHANGEOVER_LOSS", "CALIBRATION_INTERMITTENT_LOSS"],
    },
    "CALIBRATION_INTERMITTENT_LOSS": {
        "code": "CALIBRATION_TAIL_EVENT_AUDIT",
        "label": "Calibration tail-event audit",
        "cost_usd": 110.0,
        "duration_hours": 0.5,
        "question": "Are post-incident calibration delays dominated by intermittent tail events rather than transitions?",
        "discrimination": ["CALIBRATION_INTERMITTENT_LOSS", "SEQUENCE_CHANGEOVER_LOSS"],
    },
}

PROBE_TO_HYPOTHESIS = {v["code"]: k for k, v in PROBE_CATALOG.items()}


def _finite(x: Any, default: float = 0.0) -> float:
    try:
        value = float(x)
    except (TypeError, ValueError):
        return default
    return value if math.isfinite(value) else default


def _mean(xs: list[float]) -> float:
    return statistics.fmean(xs) if xs else 0.0


def _sd(xs: list[float]) -> float:
    return statistics.stdev(xs) if len(xs) >= 2 else 0.0


def _cohen_d(a: list[float], b: list[float]) -> float:
    if len(a) < 2 or len(b) < 2:
        return 0.0
    va = statistics.variance(a)
    vb = statistics.variance(b)
    denom = max(1, len(a) + len(b) - 2)
    pooled = math.sqrt(max(0.0, ((len(a)-1)*va + (len(b)-1)*vb) / denom))
    return 0.0 if pooled <= 1e-12 else (_mean(a) - _mean(b)) / pooled


def _uncertainty_state(inv: dict[str, Any]) -> dict[str, Any]:
    top = inv["top_suspect"]
    gap = _finite(inv["ambiguity"]["top_to_second_score_gap"])
    score = _finite(top["evidence_score"])
    ambiguity = inv["ambiguity"]["level"]
    if score < 55 or gap < 4 or ambiguity == "HIGH":
        state = "I_DONT_KNOW"
        label = "I DON'T KNOW"
        rationale = "Observable evidence does not separate the leading explanations strongly enough for a responsible diagnosis."
    elif score < 72 or gap < 12 or ambiguity == "MEDIUM":
        state = "CAUTIOUS"
        label = "CAUTIOUS"
        rationale = "A leading explanation exists, but uncertainty is material enough that another information-gathering step is warranted before action."
    else:
        state = "STRONG_SUSPECT"
        label = "STRONG SUSPECT"
        rationale = "The leading explanation is well separated observationally, but causal confirmation still requires an authorized intervention or DOE."
    return {
        "state": state,
        "label": label,
        "evidence_score": round(score, 2),
        "score_gap": round(gap, 2),
        "ambiguity": ambiguity,
        "rationale": rationale,
        "policy": "KAIZEN must use I DON'T KNOW when evidence is weak or competing explanations are insufficiently separated. Evidence score is not a probability.",
    }


def _voi_candidates(inv: dict[str, Any]) -> list[dict[str, Any]]:
    ranked = inv["ranked_hypotheses"]
    rank_map = {h["code"]: h for h in ranked}
    top_code = ranked[0]["code"]
    second_code = ranked[1]["code"] if len(ranked) > 1 else None
    gap = _finite(inv["ambiguity"]["top_to_second_score_gap"])
    candidates: list[dict[str, Any]] = []
    for code, meta in PROBE_CATALOG.items():
        h = rank_map[code]
        relevance = 100.0 if code == top_code else 85.0 if code == second_code else max(20.0, 65.0 - 7.0 * (int(h["rank"]) - 1))
        pair_bonus = 18.0 if top_code in meta["discrimination"] and second_code in meta["discrimination"] else 0.0
        uncertainty_bonus = max(0.0, 24.0 - min(24.0, gap))
        evidence_gap = max(0.0, 75.0 - _finite(h["evidence_score"])) * (0.18 if code in {top_code, second_code} else 0.04)
        burden = float(meta["cost_usd"]) / 80.0 + float(meta["duration_hours"]) * 3.0
        # VOI is explicitly about resolving the current decision, so probes aimed at the
        # leading/runner-up explanations dominate exploratory measurements on weak tails.
        value_score = max(0.0, min(100.0, relevance * 0.76 + pair_bonus + uncertainty_bonus + evidence_gap - burden))
        candidates.append({
            **meta,
            "hypothesis_code": code,
            "hypothesis_rank": int(h["rank"]),
            "hypothesis_target": h["target"],
            "current_evidence_score": h["evidence_score"],
            "value_of_information_score": round(value_score, 1),
            "formal_expected_value": False,
            "interpretation": "Decision-information heuristic combining current uncertainty, discrimination relevance and measurement burden; not a Bayesian monetary EV calculation.",
        })
    candidates.sort(key=lambda x: (-x["value_of_information_score"], x["cost_usd"], x["duration_hours"]))
    for i, item in enumerate(candidates, 1):
        item["rank"] = i
    return candidates


def build_active_investigation_overview(records: list[dict[str, Any]], activation_unit: int) -> dict[str, Any]:
    inv = build_investigation_overview(records, activation_unit)
    uncertainty = _uncertainty_state(inv)
    voi = _voi_candidates(inv)
    top = inv["top_suspect"]
    return {
        "uncertainty": uncertainty,
        "value_of_information": {
            "recommended_next_measurement": voi[0],
            "ranked_candidates": voi,
            "budget_note": "Probe costs are synthetic investigative-resource assumptions for the Hidden Factory demo.",
        },
        "active_investigation": {
            "leading_hypothesis": top,
            "next_step": voi[0],
            "status": "MEASURE_NEXT" if uncertainty["state"] != "STRONG_SUSPECT" else "OPTIONAL_DISCRIMINATION_BEFORE_DOE",
            "policy": "Active investigation can add observational evidence and revise beliefs, but cannot unlock causal confirmation.",
        },
        "experiment_preview": build_experiment_design(records, activation_unit),
        "causal_confirmation": {
            "level_5": "LOCKED",
            "unlock_requirement": "Authorized randomized/controlled synthetic intervention with predeclared direction, p<0.01 and |standardized effect|>=0.8.",
        },
    }


def _torque_error(r: dict[str, Any]) -> float:
    return float(r["torque_measured_nm"]) - float(r["torque_target_nm"])


def _adhesive_margin(r: dict[str, Any]) -> float:
    # Product-specific lower limits used by the factory definition.
    lsl = {"A": 5.4, "B": 5.7, "C": 6.0}
    return float(r["adhesive_strength_measured_mpa"]) - lsl[str(r["product_variant"])]


def _probe_machine(records: list[dict[str, Any]], activation_unit: int, target: str) -> tuple[float, float, str]:
    pre, post = records[:activation_unit], records[activation_unit:]
    products = sorted({str(r["product_variant"]) for r in records})
    balanced: list[float] = []
    for product in products:
        pre_t = [_torque_error(r) for r in pre if str(r["machine_id"]) == target and str(r["product_variant"]) == product]
        post_t = [_torque_error(r) for r in post if str(r["machine_id"]) == target and str(r["product_variant"]) == product]
        pre_c = [_torque_error(r) for r in pre if str(r["machine_id"]) != target and str(r["product_variant"]) == product]
        post_c = [_torque_error(r) for r in post if str(r["machine_id"]) != target and str(r["product_variant"]) == product]
        if pre_t and post_t and pre_c and post_c:
            balanced.append((_mean(post_t)-_mean(pre_t))-(_mean(post_c)-_mean(pre_c)))
    effect = _mean(balanced)
    if len(balanced) >= 2:
        test = stats.ttest_1samp(balanced, 0.0)
        p = float(test.pvalue)
    else:
        p = 1.0
    return effect, p, f"Product-balanced machine DID across {len(balanced)} represented product strata."


def _probe_gage(records: list[dict[str, Any]], activation_unit: int, target: str) -> tuple[float, float, str]:
    post = records[activation_unit:]
    a = [_torque_error(r) for r in post if str(r["gage_id"]) == target]
    b = [_torque_error(r) for r in post if str(r["gage_id"]) != target]
    if len(a) < 2 or len(b) < 2:
        return 0.0, 1.0, "Insufficient gage-stratified rows."
    test = stats.ttest_ind(a, b, equal_var=False)
    return _mean(a)-_mean(b), float(test.pvalue), "Post-incident suspect-gage vs other-gage torque-error contrast."


def _probe_fixture(records: list[dict[str, Any]], activation_unit: int, target: str) -> tuple[float, float, str]:
    post = [r for r in records[activation_unit:] if str(r["fixture_id"]) == target]
    if len(post) < 8:
        return 0.0, 1.0, "Insufficient fixture rows."
    x = [float(r["ambient_temp_c"]) for r in post]
    y = [abs(_torque_error(r)) for r in post]
    test = stats.pearsonr(x, y)
    return float(test.statistic), float(test.pvalue), "Pearson temperature association within suspect fixture on absolute torque error."


def _probe_supplier(records: list[dict[str, Any]], activation_unit: int, target: str) -> tuple[float, float, str]:
    prefix = target.split("-")[0] if "-" in target else target
    post = [r for r in records[activation_unit:] if str(r["supplier"]) == prefix]
    if len(post) < 8:
        return 0.0, 1.0, "Insufficient supplier rows."
    x = [float(r["humidity_pct"]) for r in post]
    y = [_adhesive_margin(r) for r in post]
    test = stats.pearsonr(x, y)
    return float(test.statistic), float(test.pvalue), "Humidity association with product-adjusted adhesive margin within suspect supplier."


def _transition_flags(records: list[dict[str, Any]]) -> list[bool]:
    flags: list[bool] = []
    prev = None
    for r in records:
        product = str(r["product_variant"])
        flags.append(prev is not None and product != prev)
        prev = product
    return flags


def _probe_changeover(records: list[dict[str, Any]], activation_unit: int) -> tuple[float, float, str]:
    post = records[activation_unit:]
    flags = _transition_flags(records)[activation_unit:]
    a = [float(r["calibration_s"]) for r, flag in zip(post, flags) if flag]
    b = [float(r["calibration_s"]) for r, flag in zip(post, flags) if not flag]
    if len(a) < 3 or len(b) < 3:
        return 0.0, 1.0, "Insufficient transition/non-transition rows."
    test = stats.mannwhitneyu(a, b, alternative="two-sided")
    return _mean(a)-_mean(b), float(test.pvalue), "Matched post-incident transition vs non-transition calibration-time contrast."


def _probe_microstops(records: list[dict[str, Any]], activation_unit: int) -> tuple[float, float, str]:
    pre = [float(r["calibration_s"]) for r in records[:activation_unit]]
    post = [float(r["calibration_s"]) for r in records[activation_unit:]]
    if len(pre) < 20 or len(post) < 20:
        return 0.0, 1.0, "Insufficient calibration rows."
    threshold = float(np.percentile(np.asarray(pre), 99))
    pre_hits = sum(x > threshold for x in pre)
    post_hits = sum(x > threshold for x in post)
    p1 = pre_hits/len(pre); p2 = post_hits/len(post)
    pooled = (pre_hits+post_hits)/(len(pre)+len(post))
    se = math.sqrt(max(1e-12, pooled*(1-pooled)*(1/len(pre)+1/len(post))))
    z = (p2-p1)/se
    p = 2*(1-stats.norm.cdf(abs(z)))
    return p2-p1, float(p), f"Post vs pre rate above pre-calibration P99 threshold ({threshold:.2f}s)."


def execute_observational_probe(records: list[dict[str, Any]], activation_unit: int, probe_code: str) -> dict[str, Any]:
    inv = build_investigation_overview(records, activation_unit)
    code = PROBE_TO_HYPOTHESIS.get(probe_code)
    if code is None:
        raise ValueError(f"Unknown probe_code: {probe_code}")
    hypothesis = next(h for h in inv["ranked_hypotheses"] if h["code"] == code)
    target = str(hypothesis["target"])

    if code == "MACHINE_TORQUE_BIAS":
        effect, p, detail = _probe_machine(records, activation_unit, target)
    elif code == "GAGE_MEASUREMENT_DRIFT":
        effect, p, detail = _probe_gage(records, activation_unit, target)
    elif code == "FIXTURE_ENVIRONMENT_INTERACTION":
        effect, p, detail = _probe_fixture(records, activation_unit, target)
    elif code == "SUPPLIER_HUMIDITY_INTERACTION":
        effect, p, detail = _probe_supplier(records, activation_unit, target)
    elif code == "SEQUENCE_CHANGEOVER_LOSS":
        effect, p, detail = _probe_changeover(records, activation_unit)
    else:
        effect, p, detail = _probe_microstops(records, activation_unit)

    statistical_strength = min(5.0, max(0.0, -math.log10(max(1e-300, p)))) / 5.0
    effect_strength = min(1.0, abs(effect) / (0.5 if code in {"MACHINE_TORQUE_BIAS", "GAGE_MEASUREMENT_DRIFT"} else 0.2))
    support_score = round(100*(0.6*statistical_strength + 0.4*effect_strength), 1)
    supports = p < 0.05 and abs(effect) > 1e-8

    updated = []
    for h in inv["ranked_hypotheses"]:
        new_score = float(h["evidence_score"])
        if h["code"] == code:
            new_score += (support_score - 50.0) * 0.18
        elif h["code"] in PROBE_CATALOG[code]["discrimination"]:
            new_score -= max(0.0, support_score - 50.0) * 0.06
        updated.append({"code": h["code"], "title": h["title"], "target": h["target"], "prior_score": h["evidence_score"], "updated_score": round(max(0.0,min(100.0,new_score)),1)})
    updated.sort(key=lambda x: x["updated_score"], reverse=True)

    prior_leader = inv["top_suspect"]["code"]
    new_leader = updated[0]["code"]
    return {
        "probe": {**PROBE_CATALOG[code], "hypothesis_code": code, "target": target},
        "result": {
            "effect": round(float(effect), 6),
            "p_value": round(float(p), 12),
            "support_score": support_score,
            "supports_target_hypothesis": bool(supports),
            "detail": detail,
        },
        "belief_update": {
            "prior_leader": prior_leader,
            "updated_leader": new_leader,
            "changed_leader": new_leader != prior_leader,
            "ranking": updated,
            "policy": "Probe updates are a transparent decision-support heuristic layered on new observational evidence; they do not establish causality.",
        },
        "causal_confirmation_unlocked": False,
    }


EXPERIMENT_PLANS: dict[str, dict[str, Any]] = {
    "MACHINE_TORQUE_BIAS": {
        "experiment_code": "DOE_TOOL_RECALIBRATION",
        "title": "Randomized torque-tool recalibration confirmation",
        "factor": "M2 tool condition",
        "levels": ["current calibration", "recalibrated"],
        "primary_response": "absolute torque error (Nm)",
        "improvement_direction": "DECREASE",
        "blocks": ["product variant", "shift"],
        "randomization": "Randomize eligible M2 units to current-vs-recalibrated tool condition within product blocks.",
    },
    "GAGE_MEASUREMENT_DRIFT": {
        "experiment_code": "DOE_GAGE_RECALIBRATION",
        "title": "Randomized cross-gage calibration confirmation",
        "factor": "G2 gage condition",
        "levels": ["current zero", "recalibrated against reference"],
        "primary_response": "absolute reference measurement error (Nm)",
        "improvement_direction": "DECREASE",
        "blocks": ["reference part", "operator"],
        "randomization": "Randomize repeated reference parts across current/recalibrated G2 condition and operator order.",
    },
    "FIXTURE_ENVIRONMENT_INTERACTION": {
        "experiment_code": "DOE_FIXTURE_THERMAL",
        "title": "2×2 fixture-condition × temperature confirmation",
        "factor": "fixture condition × thermal band",
        "levels": ["current F4 / nominal temp", "current F4 / elevated temp", "restored F4 / nominal temp", "restored F4 / elevated temp"],
        "primary_response": "absolute torque error (Nm)",
        "improvement_direction": "DECREASE",
        "blocks": ["product variant"],
        "randomization": "Randomize product-balanced units across fixture-condition and controlled thermal cells.",
    },
    "SUPPLIER_HUMIDITY_INTERACTION": {
        "experiment_code": "DOE_RESIN_HUMIDITY",
        "title": "2×2 resin-lot × humidity confirmation",
        "factor": "resin lot × humidity band",
        "levels": ["suspect/current humidity", "suspect/high humidity", "control/current humidity", "control/high humidity"],
        "primary_response": "adhesive strength margin (MPa)",
        "improvement_direction": "INCREASE",
        "blocks": ["product variant"],
        "randomization": "Randomize specimens across resin-lot and humidity cells within product blocks.",
    },
    "CALIBRATION_INTERMITTENT_LOSS": {
        "experiment_code": "DOE_SENSOR_SERVICE",
        "title": "Randomized calibration sensor-service confirmation",
        "factor": "sensor handshake condition",
        "levels": ["current", "serviced"],
        "primary_response": "calibration service time (s)",
        "improvement_direction": "DECREASE",
        "blocks": ["product variant"],
        "randomization": "Alternate randomized production windows between current and serviced handshake configuration.",
    },
    "SEQUENCE_CHANGEOVER_LOSS": {
        "experiment_code": "DOE_CHANGEOVER_STANDARD_WORK",
        "title": "Randomized crossover of changeover standard work",
        "factor": "changeover method",
        "levels": ["current method", "restored standard work"],
        "primary_response": "transition calibration time (s)",
        "improvement_direction": "DECREASE",
        "blocks": ["from→to product transition"],
        "randomization": "Randomize matched product-transition opportunities to current/restored standard-work method.",
    },
}

EXPERIMENT_TO_HYPOTHESIS = {v["experiment_code"]: k for k, v in EXPERIMENT_PLANS.items()}


def build_experiment_design(records: list[dict[str, Any]], activation_unit: int) -> dict[str, Any]:
    inv = build_investigation_overview(records, activation_unit)
    top = inv["top_suspect"]
    plan = dict(EXPERIMENT_PLANS[top["code"]])
    intervention_code = HYPOTHESIS_TO_INTERVENTION.get(top["code"])
    intervention = INTERVENTION_CATALOG.get(intervention_code or "", {})
    plan.update({
        "hypothesis_code": top["code"],
        "target": top["target"],
        "observational_evidence_score": top["evidence_score"],
        "recommended_intervention_code": intervention_code,
        "recommended_intervention": intervention.get("label"),
        "planned_sample_size": 160,
        "alpha": 0.01,
        "minimum_standardized_effect": 0.8,
        "predeclared_success_rule": "Correct improvement direction AND Welch p<0.01 AND |Cohen d|>=0.8.",
        "causal_policy": "Design is generated from observable diagnosis only. Execution may use the Hidden Factory as a controlled synthetic test bed, but hidden truth is not exposed to the investigator.",
    })
    return plan


def _baseline_experiment_metric(records: list[dict[str, Any]], activation_unit: int, code: str, target: str) -> tuple[float,float,str]:
    post = records[activation_unit:]
    if code == "MACHINE_TORQUE_BIAS":
        vals = [abs(_torque_error(r)) for r in post if str(r["machine_id"]) == target]
        return _mean(vals), max(0.05,_sd(vals)), "DECREASE"
    if code == "GAGE_MEASUREMENT_DRIFT":
        vals = [abs(_torque_error(r)) for r in post if str(r["gage_id"]) == target]
        return _mean(vals), max(0.05,_sd(vals)), "DECREASE"
    if code == "FIXTURE_ENVIRONMENT_INTERACTION":
        vals = [abs(_torque_error(r)) for r in post if str(r["fixture_id"]) == target]
        return _mean(vals), max(0.05,_sd(vals)), "DECREASE"
    if code == "SUPPLIER_HUMIDITY_INTERACTION":
        prefix = target.split("-")[0]
        vals = [_adhesive_margin(r) for r in post if str(r["supplier"]) == prefix]
        return _mean(vals), max(0.05,_sd(vals)), "INCREASE"
    if code == "SEQUENCE_CHANGEOVER_LOSS":
        flags = _transition_flags(records)[activation_unit:]
        vals = [float(r["calibration_s"]) for r,flag in zip(post,flags) if flag]
        return _mean(vals), max(0.5,_sd(vals)), "DECREASE"
    vals = [float(r["calibration_s"]) for r in post]
    return _mean(vals), max(0.5,_sd(vals)), "DECREASE"


def _expected_matches(scenario_code: str, hypothesis_code: str, target: str) -> bool:
    expected = EXPECTED_ATTRIBUTION.get(scenario_code) or {}
    if expected.get("code") != hypothesis_code:
        return False
    if "target" in expected:
        return target == expected["target"]
    prefix = str(expected.get("target_prefix") or "")
    return target.startswith(prefix)


def execute_controlled_experiment(
    records: list[dict[str, Any]], activation_unit: int, scenario_code: str, experiment_code: str, *, seed: int
) -> dict[str, Any]:
    hypothesis_code = EXPERIMENT_TO_HYPOTHESIS.get(experiment_code)
    if hypothesis_code is None:
        raise ValueError(f"Unknown experiment_code: {experiment_code}")
    inv = build_investigation_overview(records, activation_unit)
    hypothesis = next(h for h in inv["ranked_hypotheses"] if h["code"] == hypothesis_code)
    target = str(hypothesis["target"])
    plan = dict(EXPERIMENT_PLANS[hypothesis_code])
    mean, sd, direction = _baseline_experiment_metric(records, activation_unit, hypothesis_code, target)
    correct = _expected_matches(scenario_code, hypothesis_code, target)

    stable = int(hashlib.sha256(f"{seed}|{scenario_code}|{experiment_code}|{target}".encode()).hexdigest()[:8],16)
    rng = np.random.default_rng(stable)
    n_arm = 80
    control = rng.normal(mean, sd, n_arm)
    magnitude = 1.15*sd if correct else 0.10*sd
    treated_mean = mean - magnitude if direction == "DECREASE" else mean + magnitude
    treatment = rng.normal(treated_mean, sd, n_arm)
    test = stats.ttest_ind(treatment, control, equal_var=False)
    effect = _cohen_d(treatment.tolist(), control.tolist())
    delta = float(np.mean(treatment)-np.mean(control))
    direction_ok = delta < 0 if direction == "DECREASE" else delta > 0
    p = float(test.pvalue)
    confirmed = bool(direction_ok and p < 0.01 and abs(effect) >= 0.8)

    return {
        "experiment": {
            **plan,
            "hypothesis_code": hypothesis_code,
            "target": target,
            "n_control": n_arm,
            "n_treatment": n_arm,
            "alpha": 0.01,
            "minimum_standardized_effect": 0.8,
        },
        "aggregate_results": {
            "control_mean": round(float(np.mean(control)),6),
            "treatment_mean": round(float(np.mean(treatment)),6),
            "difference_treatment_minus_control": round(delta,6),
            "welch_t": round(float(test.statistic),6),
            "p_value": round(p,12),
            "cohen_d": round(effect,4),
            "improvement_direction": direction,
            "direction_passed": direction_ok,
        },
        "causal_confirmation": {
            "level": 5,
            "passed": confirmed,
            "status": "CONFIRMED_IN_SYNTHETIC_DOE" if confirmed else "NOT_CONFIRMED",
            "predeclared_rule": "Correct improvement direction AND Welch p<0.01 AND |Cohen d|>=0.8.",
            "note": "Confirmation is valid only inside the controlled synthetic Hidden Factory experiment; it is not real-world causal validation.",
        },
        "belief_revision": {
            "prior_leader": inv["top_suspect"]["code"],
            "tested_hypothesis": hypothesis_code,
            "outcome": "SUPPORTED" if confirmed else "FAILED_CONFIRMATION",
            "next_leader_if_failed": next((h["code"] for h in inv["ranked_hypotheses"] if h["code"] != hypothesis_code), None),
            "audit_message": (
                "The controlled experiment met every predeclared confirmation criterion; the synthetic causal gate may unlock."
                if confirmed else
                "The tested observational hypothesis failed the predeclared causal confirmation rule; KAIZEN must revise rather than defend the old belief."
            ),
        },
        "truth_boundary": {
            "scenario_code_exposed_in_output": False,
            "ground_truth_exposed_in_output": False,
            "hidden_factory_used_only_to_generate_controlled_experimental_response": True,
        },
    }


def freeze_human_prediction(records: list[dict[str, Any]], activation_unit: int, hypothesis_code: str) -> dict[str, Any]:
    inv = build_investigation_overview(records, activation_unit)
    match = next((h for h in inv["ranked_hypotheses"] if h["code"] == hypothesis_code), None)
    if match is None:
        raise ValueError("hypothesis_code must be one of the currently ranked hypotheses")
    attr = match.get("attribution") or {}
    return {
        "code": match["code"],
        "title": match["title"],
        "target": match["target"],
        "direction": attr.get("direction"),
        "interaction_partner": attr.get("interaction_partner"),
        "frozen": True,
        "note": "Human prediction is frozen before truth reveal; changing it after reveal is not allowed.",
    }


def _target_match(predicted: str, expected: dict[str, Any]) -> bool:
    if "target" in expected:
        return predicted == expected["target"]
    return predicted.startswith(str(expected.get("target_prefix") or ""))


def score_human_prediction(prediction: dict[str, Any], scenario_code: str) -> dict[str, Any]:
    expected = EXPECTED_ATTRIBUTION.get(scenario_code)
    if expected is None:
        raise ValueError("No scoring policy for scenario")
    checks = {
        "mechanism_family": prediction.get("code") == expected.get("code"),
        "affected_target": _target_match(str(prediction.get("target") or ""), expected),
        "direction": prediction.get("direction") == expected.get("direction"),
        "interaction_partner": prediction.get("interaction_partner") == expected.get("interaction"),
    }
    correct = sum(int(v) for v in checks.values())
    return {
        "score": round(100*correct/4,1),
        "dimensions_correct": correct,
        "dimensions_total": 4,
        "checks": checks,
        "grade": "FULL_ATTRIBUTION_MATCH" if correct == 4 else "PARTIAL_MATCH" if correct else "MISDIAGNOSIS",
        "prediction": prediction,
        "benchmark_note": "Human-vs-AI score is valid only for the synthetic Hidden Factory scenario.",
    }
