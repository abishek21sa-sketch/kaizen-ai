# KAIZEN AI V0.7.0 — Manual Acceptance Tests

Use a **freshly extracted V0.7.0 folder**. Close older KAIZEN command windows first.

## 1 — Startup/build sync

Run `START_KAIZEN.bat`.

Expected:

- browser opens around `127.0.0.1:9070` (or next free port);
- title says **Improvement Portfolio Optimizer V0.7.0**;
- health badge says **OK / 0.7.0 · 20260815-v070-opt1**;
- no BUILD MISMATCH warning.

## 2 — Reference blind case

Use:

- Seed: `42`
- Units: `2500`

Click **BREAK THE FACTORY**.

Expected pre-existing behavior:

- Statistical Investigator leading suspect: `M2`;
- frozen arena prediction: `M2 · INCREASE`;
- ground truth is still sealed.

## 3 — Default optimizer solve

Scroll to **DECIDE / IMPROVEMENT PORTFOLIO OPTIMIZER**.

Default inputs should be:

- Budget `$25,000`
- Max downtime `8 h`
- Min good throughput `80 /h`
- Max defect `100%`
- Annual volume `200000`
- Effectiveness `100%`
- Demand `1.00`
- Min evidence score `25`

Expected:

- status: **OPTIMAL**;
- selected portfolio includes **Recalibrate torque tool** and should contain no low-evidence unrelated actions under the default evidence gate;
- cost is within `$25,000`;
- downtime is within `8 h`;
- counterfactual good throughput is at least `80/h`;
- first-year net value is positive;
- solver text states exact binary portfolio enumeration and safe pruning.

## 4 — Budget constraint

Set budget to `$1,000` and click **OPTIMIZE PORTFOLIO**.

Expected:

- torque-tool recalibration cannot be selected because its modeled cost is `$1,250`;
- solver never returns a portfolio above the entered budget.

## 5 — Infeasible throughput request

Restore budget to `$25,000` and set minimum good throughput to `500 /h`.

Expected:

- status becomes **INFEASIBLE**;
- UI says no portfolio satisfies all hard constraints;
- no fabricated solution appears.

Restore minimum good throughput to `80 /h` afterward.

## 6 — Evidence gate

Set minimum evidence score to `95` for the seed-42 case and optimize.

Expected:

- M2 action is excluded because its observational evidence score is below 95;
- optimizer does not silently bypass the evidence gate.

Restore evidence score to `25`.

## 7 — Reveal independence

Record the default optimal portfolio, then use **REVEAL + SCORE**.

Run the optimizer again with the same settings.

Expected:

- selected portfolio and numeric solution remain unchanged;
- the optimizer does not consume revealed ground truth.

## 8 — Existing input validation regression

Enter `50` units and click **BREAK THE FACTORY**.

Expected readable message:

`Units must be a whole number between 100 and 250,000.`

No `[object Object]` error.
