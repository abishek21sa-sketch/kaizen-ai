from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

import numpy as np
from scipy import stats


@dataclass(frozen=True)
class TestResult:
    test: str
    statistic: float | None
    p_value: float | None
    effect: float | None
    n: int
    detail: str
    confidence_interval: tuple[float, float] | None = None

    def to_dict(self) -> dict:
        return {
            "test": self.test,
            "statistic": _finite_or_none(self.statistic),
            "p_value": _finite_or_none(self.p_value),
            "effect": _finite_or_none(self.effect),
            "n": int(self.n),
            "detail": self.detail,
            "confidence_interval_95": [round(float(x), 8) for x in self.confidence_interval] if self.confidence_interval is not None else None,
        }


def _finite_or_none(x: float | None) -> float | None:
    if x is None:
        return None
    x = float(x)
    return x if math.isfinite(x) else None


def _array(values: Iterable[float]) -> np.ndarray:
    arr = np.asarray(list(values), dtype=float)
    return arr[np.isfinite(arr)]


def mean_sd(values: Iterable[float]) -> tuple[float, float, int]:
    x = _array(values)
    if len(x) == 0:
        return 0.0, 0.0, 0
    return float(np.mean(x)), float(np.std(x, ddof=1)) if len(x) > 1 else 0.0, int(len(x))


def pooled_sd(a: Iterable[float], b: Iterable[float]) -> float:
    x, y = _array(a), _array(b)
    if len(x) < 2 or len(y) < 2:
        return 0.0
    denom = len(x) + len(y) - 2
    if denom <= 0:
        return 0.0
    v = ((len(x) - 1) * np.var(x, ddof=1) + (len(y) - 1) * np.var(y, ddof=1)) / denom
    return float(math.sqrt(max(0.0, v)))


def cohens_d(a: Iterable[float], b: Iterable[float]) -> float:
    x, y = _array(a), _array(b)
    psd = pooled_sd(x, y)
    if psd <= 1e-12:
        return 0.0
    return float((np.mean(a if isinstance(a, np.ndarray) else x) - np.mean(b if isinstance(b, np.ndarray) else y)) / psd)


def welch(a: Iterable[float], b: Iterable[float], *, label: str) -> TestResult:
    x, y = _array(a), _array(b)
    n = len(x) + len(y)
    if len(x) < 2 or len(y) < 2:
        return TestResult("Welch t-test", None, None, None, n, f"{label}: insufficient observations")
    res = stats.ttest_ind(x, y, equal_var=False, nan_policy="omit")
    effect = cohens_d(x, y)
    vx, vy = float(np.var(x, ddof=1)), float(np.var(y, ddof=1))
    se2 = vx / len(x) + vy / len(y)
    diff = float(np.mean(x) - np.mean(y))
    if se2 > 0:
        df_num = se2 * se2
        df_den = (vx / len(x)) ** 2 / (len(x) - 1) + (vy / len(y)) ** 2 / (len(y) - 1)
        df = df_num / df_den if df_den > 0 else max(1, len(x) + len(y) - 2)
        crit = float(stats.t.ppf(0.975, df))
        ci = (diff - crit * math.sqrt(se2), diff + crit * math.sqrt(se2))
    else:
        ci = (diff, diff)
    return TestResult(
        "Welch t-test",
        float(res.statistic),
        float(res.pvalue),
        effect,
        n,
        f"{label}; Cohen's d uses pooled sample SD; CI is for raw mean difference",
        confidence_interval=ci,
    )


def mann_whitney(a: Iterable[float], b: Iterable[float], *, label: str) -> TestResult:
    x, y = _array(a), _array(b)
    n = len(x) + len(y)
    if len(x) < 2 or len(y) < 2:
        return TestResult("Mann-Whitney U", None, None, None, n, f"{label}: insufficient observations")
    res = stats.mannwhitneyu(x, y, alternative="two-sided")
    # Rank-biserial correlation; sign positive when group A tends larger.
    u = float(res.statistic)
    rbc = (2.0 * u / (len(x) * len(y))) - 1.0
    return TestResult("Mann-Whitney U", u, float(res.pvalue), rbc, n, f"{label}; effect is rank-biserial correlation")


def pearson(x_values: Iterable[float], y_values: Iterable[float], *, label: str) -> TestResult:
    x, y = _array(x_values), _array(y_values)
    n = min(len(x), len(y))
    if n < 3:
        return TestResult("Pearson correlation", None, None, None, n, f"{label}: insufficient observations")
    x, y = x[:n], y[:n]
    if np.std(x) < 1e-12 or np.std(y) < 1e-12:
        return TestResult("Pearson correlation", None, None, 0.0, n, f"{label}: zero variance")
    res = stats.pearsonr(x, y)
    r = float(res.statistic)
    if n > 3 and abs(r) < 1:
        z = math.atanh(r)
        se = 1.0 / math.sqrt(n - 3)
        ci = (math.tanh(z - 1.96 * se), math.tanh(z + 1.96 * se))
    else:
        ci = (r, r)
    return TestResult("Pearson correlation", r, float(res.pvalue), r, n, f"{label}; CI is Fisher-z 95% CI for r", confidence_interval=ci)


def proportion_test(success_a: int, n_a: int, success_b: int, n_b: int, *, label: str) -> TestResult:
    if min(n_a, n_b) <= 0:
        return TestResult("Two-proportion z-test", None, None, None, n_a + n_b, f"{label}: insufficient observations")
    p1, p2 = success_a / n_a, success_b / n_b
    pooled = (success_a + success_b) / (n_a + n_b)
    se = math.sqrt(max(0.0, pooled * (1.0 - pooled) * (1.0 / n_a + 1.0 / n_b)))
    if se <= 1e-12:
        z = 0.0
        p = 1.0
    else:
        z = (p1 - p2) / se
        p = 2.0 * stats.norm.sf(abs(z))
    # Risk difference is more interpretable than an odds ratio here.
    rd = p1 - p2
    ci_se = math.sqrt(max(0.0, p1 * (1-p1) / n_a + p2 * (1-p2) / n_b))
    ci = (rd - 1.96 * ci_se, rd + 1.96 * ci_se)
    return TestResult("Two-proportion z-test", z, p, rd, n_a + n_b, f"{label}; effect is risk difference; CI is unpooled normal 95% CI", confidence_interval=ci)


def did_continuous(
    pre_target: Iterable[float],
    pre_other: Iterable[float],
    post_target: Iterable[float],
    post_other: Iterable[float],
    *,
    label: str,
) -> TestResult:
    """Difference-in-differences contrast for four independent cells.

    Uses a normal approximation for the contrast SE. This is deliberately
    transparent and dependency-light; V0.4 reports the result as observational
    evidence, not a causal estimate.
    """
    groups = [_array(x) for x in (pre_target, pre_other, post_target, post_other)]
    n = sum(len(g) for g in groups)
    if any(len(g) < 2 for g in groups):
        return TestResult("Difference-in-differences", None, None, None, n, f"{label}: insufficient observations")
    m = [float(np.mean(g)) for g in groups]
    v = [float(np.var(g, ddof=1)) for g in groups]
    effect = (m[2] - m[3]) - (m[0] - m[1])
    se2 = sum(v_i / len(g) for v_i, g in zip(v, groups))
    if se2 <= 1e-18:
        z, p = 0.0, 1.0
    else:
        z = effect / math.sqrt(se2)
        p = 2.0 * stats.norm.sf(abs(z))
    baseline_sd = pooled_sd(np.concatenate([groups[0], groups[1]]), np.concatenate([groups[2], groups[3]]))
    standardized = effect / baseline_sd if baseline_sd > 1e-12 else 0.0
    raw_se = math.sqrt(se2) if se2 > 0 else 0.0
    ci = (effect - 1.96 * raw_se, effect + 1.96 * raw_se)
    return TestResult(
        "Difference-in-differences",
        z,
        p,
        standardized,
        n,
        f"{label}; raw DID={effect:.6g}; effect standardized by pooled outcome SD; CI is for raw DID",
        confidence_interval=ci,
    )


def significance_strength(p: float | None) -> float:
    """Map a p-value to [0,1] without pretending it is posterior probability."""
    if p is None or not math.isfinite(p):
        return 0.0
    if p <= 1e-8:
        return 1.0
    if p >= 0.10:
        return 0.0
    # Smoothly maps .10 -> 0 and 1e-8 -> 1 on log scale.
    return float(min(1.0, max(0.0, (-math.log10(p) - 1.0) / 7.0)))


def bounded_effect(effect: float | None, reference: float = 0.8) -> float:
    if effect is None or not math.isfinite(effect) or reference <= 0:
        return 0.0
    return float(min(1.0, abs(effect) / reference))
