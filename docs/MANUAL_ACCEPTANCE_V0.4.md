# KAIZEN AI V0.4 — Target-Laptop Acceptance Tests

Use the normal browser UI unless a test explicitly says otherwise.

## A. Startup

1. Extract V0.4 into a fresh folder.
2. Double-click `START_KAIZEN.bat`.
3. Confirm the browser opens and the health badge says `OK / 0.4.0`.

**PASS:** Statistical Investigator V0.4 loads without traceback or blank page.

## B. Default blind investigation

Use:

- Seed: `42`
- Units: `2500`

Click **BREAK THE FACTORY**.

**PASS:**

- Ground truth remains sealed.
- Lean Six Sigma section populates.
- IE section populates.
- Statistical Investigator section populates.
- Leading suspect is centered on **M2 / machine-tool bias** for this deterministic seed.
- Evidence score is shown as `/100` and the UI explicitly says it is not a probability.
- Status is a suspect/association label, never “confirmed root cause”.

## C. Ranked competing hypotheses

Scroll to **COMPETING HYPOTHESES**.

**PASS:** six hypotheses are ranked with score, status, primary p-value and effect size.

## D. Correlation ≠ Cause Gate

Scroll to the gate.

**PASS:**

- L0–L4 may show passed depending on evidence.
- L5 **Intervention / DOE confirmation** remains locked/not passed.
- Policy text explicitly forbids causal confirmation from V0.4 observational evidence.

## E. Adjusted regression + ANOVA

Scroll to **ADJUSTED REGRESSION** and **FACTORIAL ANOVA**.

**PASS:**

- model badge should normally show `5/5 MODELS FIT` for the default run;
- regression rows show term, estimate/odds ratio, p-value and 95% CI;
- ANOVA rows show factors/interactions with F and p-values;
- no `NaN`, `undefined`, `[object Object]` or broken table appears.

## F. Evidence ledger

Scroll to **EVIDENCE LEDGER**.

**PASS:**

- unique `EVD-xxxx` IDs appear;
- tests are labeled PRIMARY or CORROBORATING;
- p-values/effects/N/detail are populated;
- ledger contains no hidden scenario/root-cause labels.

## G. Confounder checks

Scroll to **CONFOUNDER CHECKS**.

**PASS:** operator, shift and product checks appear and are explicitly described as potential confounders rather than causes.

## H. Ground-truth independence

Before reveal, note the leading hypothesis and score.

Click **REVEAL GROUND TRUTH**.

**PASS:** truth becomes visible, but the already computed investigator evidence does not silently relabel itself as causal confirmation.

## I. New incident reseals truth

After reveal, click **BREAK THE FACTORY** again.

**PASS:** new incident ground truth is sealed and reveal button resets.

## J. Input validation regression

Enter Units = `50` and click **BREAK THE FACTORY**.

**PASS:** readable message says units must be between 100 and 250,000.

## Optional mechanism checks

These are not required if B–J pass, but they are useful visually:

- Seed `1`, 2500 units: flow/changeover stress should produce a queueing/capacity-led investigation.
- Additional seeds can be tried to see competing hypotheses change without exposing ground truth first.
