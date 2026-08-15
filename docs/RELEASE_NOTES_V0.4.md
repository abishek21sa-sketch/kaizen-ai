# KAIZEN AI V0.4.0 — Statistical Investigator

V0.4 introduces the first blind ANALYZE-phase investigator.

## Added

- Ranked competing hypotheses across six mechanism classes.
- Difference-in-differences screening.
- Welch, Mann-Whitney, proportion and Pearson tests.
- Effect sizes and 95% confidence intervals where appropriate.
- Adjusted OLS regression with HC3 covariance.
- Binomial logistic regression.
- Factorial ANOVA.
- Post-event interaction terms.
- Operator/shift/product confounder checks.
- Evidence ledger with unique evidence IDs.
- Explicit non-probabilistic evidence score.
- Correlation ≠ Cause Gate with locked intervention/DOE level.
- Statistical Investigator UI.
- Adjusted Regression and Factorial ANOVA UI sections.
- API endpoint: `GET /api/runs/{run_id}/investigation/overview`.

## Causal boundary

The investigator accepts only observable records and the incident activation boundary. It does not accept scenario code, latent records or revealed ground truth.

A hypothesis may be `STRONG_SUSPECT`, but remains `NOT_CONFIRMED`.

## Validation

- 49 automated tests pass in the development tree.
- 8/8 startup diagnostics pass.
- 36/36 Top-1 mechanism-family identification across 6 seeds × 6 synthetic incident families in the V0.4 blind benchmark.
- Clean-extracted package validation is required before release handoff.

## Not yet implemented

- scored reveal / benchmark UI;
- incident investigation timeline;
- intervention simulation;
- DOE execution;
- constrained improvement optimization;
- Gemini AI reasoning;
- Red Team / Human vs AI / Value of Information.
