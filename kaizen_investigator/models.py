from __future__ import annotations

import math
import warnings
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.stats.anova import anova_lm


def _clean_float(x: Any) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _coef_table(model, *, only_terms: tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    conf = model.conf_int(alpha=0.05)
    out: list[dict[str, Any]] = []
    for term in model.params.index:
        if term == "Intercept":
            continue
        if only_terms and not any(token in term for token in only_terms):
            continue
        lo, hi = conf.loc[term]
        out.append(
            {
                "term": str(term),
                "estimate": _clean_float(model.params.loc[term]),
                "std_error": _clean_float(model.bse.loc[term]),
                "statistic": _clean_float(model.tvalues.loc[term]),
                "p_value": _clean_float(model.pvalues.loc[term]),
                "confidence_interval_95": [_clean_float(lo), _clean_float(hi)],
            }
        )
    out.sort(key=lambda x: (1.0 if x["p_value"] is None else x["p_value"], -(abs(x["estimate"] or 0.0))))
    return out


def _fit_ols(df: pd.DataFrame, formula: str, *, name: str, terms: tuple[str, ...] | None = None) -> dict[str, Any]:
    try:
        model = smf.ols(formula, data=df).fit(cov_type="HC3")
        return {
            "name": name,
            "model_type": "OLS with HC3 robust covariance",
            "formula": formula,
            "n": int(model.nobs),
            "r_squared": _clean_float(model.rsquared),
            "adjusted_r_squared": _clean_float(model.rsquared_adj),
            "status": "FIT",
            "coefficients": _coef_table(model, only_terms=terms),
            "interpretation_limit": "Observational adjusted regression; coefficients are not causal effects.",
        }
    except Exception as exc:
        return {
            "name": name,
            "model_type": "OLS with HC3 robust covariance",
            "formula": formula,
            "status": "FAILED",
            "error": f"{type(exc).__name__}: {exc}",
            "coefficients": [],
        }


def _fit_logistic(df: pd.DataFrame) -> dict[str, Any]:
    formula = (
        "observed_defect ~ post + C(machine_id) + C(gage_id) + C(fixture_id) + C(product_variant) "
        "+ post:C(machine_id) + post:C(gage_id) + post:C(fixture_id)"
    )
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = smf.glm(formula, data=df, family=sm.families.Binomial()).fit(cov_type="HC3", maxiter=200)
        conf = model.conf_int(alpha=0.05)
        rows = []
        for term in model.params.index:
            if term == "Intercept":
                continue
            beta = float(model.params.loc[term])
            lo, hi = conf.loc[term]
            rows.append(
                {
                    "term": str(term),
                    "log_odds": _clean_float(beta),
                    "odds_ratio": _clean_float(math.exp(max(-50.0, min(50.0, beta)))),
                    "p_value": _clean_float(model.pvalues.loc[term]),
                    "confidence_interval_95_or": [
                        _clean_float(math.exp(max(-50.0, min(50.0, float(lo))))),
                        _clean_float(math.exp(max(-50.0, min(50.0, float(hi))))),
                    ],
                }
            )
        rows.sort(key=lambda x: (1.0 if x["p_value"] is None else x["p_value"]))
        return {
            "name": "Observed defect logistic model",
            "model_type": "Binomial GLM with HC3 robust covariance",
            "formula": formula,
            "n": int(model.nobs),
            "status": "FIT",
            "coefficients": rows,
            "interpretation_limit": "Odds ratios are adjusted associations, not causal effects.",
        }
    except Exception as exc:
        return {
            "name": "Observed defect logistic model",
            "model_type": "Binomial GLM",
            "formula": formula,
            "status": "FAILED",
            "error": f"{type(exc).__name__}: {exc}",
            "coefficients": [],
        }


def _anova(df: pd.DataFrame) -> dict[str, Any]:
    formula = (
        "torque_error_nm ~ post + C(machine_id) + C(gage_id) + C(fixture_id) + C(operator_id) + C(product_variant) "
        "+ post:C(machine_id) + post:C(gage_id) + post:C(fixture_id)"
    )
    try:
        base = smf.ols(formula, data=df).fit()
        try:
            table = anova_lm(base, typ=2, robust="hc3")
            method = "Type-II ANOVA with HC3 robust covariance"
        except TypeError:
            table = anova_lm(base, typ=2)
            method = "Type-II ANOVA"
        rows = []
        for term, row in table.iterrows():
            if str(term).lower() == "residual":
                continue
            rows.append(
                {
                    "term": str(term),
                    "sum_sq": _clean_float(row.get("sum_sq")),
                    "df": _clean_float(row.get("df")),
                    "f_statistic": _clean_float(row.get("F")),
                    "p_value": _clean_float(row.get("PR(>F)")),
                }
            )
        rows.sort(key=lambda x: 1.0 if x["p_value"] is None else x["p_value"])
        return {
            "name": "Torque-error factorial screening ANOVA",
            "model_type": method,
            "formula": formula,
            "n": int(base.nobs),
            "status": "FIT",
            "terms": rows,
            "interpretation_limit": "ANOVA identifies adjusted association/interaction signals; it does not establish mechanism causality.",
        }
    except Exception as exc:
        return {
            "name": "Torque-error factorial screening ANOVA",
            "model_type": "Type-II ANOVA",
            "formula": formula,
            "status": "FAILED",
            "error": f"{type(exc).__name__}: {exc}",
            "terms": [],
        }


def build_adjusted_models(df: pd.DataFrame) -> dict[str, Any]:
    """Fit adjusted observational models using only columns in the observable frame."""
    torque_formula = (
        "torque_error_nm ~ post * (C(machine_id) + C(gage_id) + C(fixture_id)) "
        "+ C(operator_id) + C(product_variant) + ambient_temp_c + post:ambient_temp_c"
    )
    calibration_formula = "calibration_s ~ post * transition + C(product_variant)"
    adhesive_formula = (
        "adhesive_margin_mpa ~ post * C(supplier) + humidity_pct + post:humidity_pct + C(product_variant)"
    )
    ols_models = [
        _fit_ols(df, torque_formula, name="Adjusted torque-error model", terms=("post:", "post:C", "ambient_temp")),
        _fit_ols(df, calibration_formula, name="Calibration transition-interaction model", terms=("post:transition", "post", "transition")),
        _fit_ols(df, adhesive_formula, name="Adjusted adhesive-margin model", terms=("post:C(supplier)", "post:humidity", "humidity", "post")),
    ]
    logistic = _fit_logistic(df)
    anova = _anova(df)
    fitted = sum(1 for m in [*ols_models, logistic, anova] if m.get("status") == "FIT")
    return {
        "status": "FIT" if fitted >= 4 else "PARTIAL",
        "models_fit": fitted,
        "models_attempted": 5,
        "ols": ols_models,
        "logistic": logistic,
        "anova": anova,
        "policy": "All models use observable fields only. Robust/adjusted association is stronger evidence than a raw correlation, but is still not causal confirmation.",
    }
