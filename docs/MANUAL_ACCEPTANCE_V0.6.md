# KAIZEN AI V0.6.0 — Manual Acceptance Tests

Use a **freshly extracted V0.6.0 folder**. Close older KAIZEN command windows first.

## 1 — Build identity

Run `START_KAIZEN.bat`.

Expected:

- browser opens around `127.0.0.1:8960` (or the next free port);
- title says **Process Simulation Lab V0.6.0**;
- health badge says **OK / 0.6.0 · 20260815-v060-sim1**;
- no BUILD MISMATCH banner.

## 2 — Reference incident

Use:

- Seed: `42`
- Units: `2500`

Click **BREAK THE FACTORY**.

Expected blind diagnosis before reveal:

- leading suspect is `M2`;
- direction is `INCREASE`;
- causal confirmation remains locked.

## 3 — Simulation section appears

Scroll to **IMPROVE / PROCESS SIMULATION**.

Expected:

- state shows `IMPLEMENTED AND TESTED`;
- recommended action is **Recalibrate torque tool**;
- baseline and counterfactual cards populate;
- defect rate and COPQ should materially improve under the recommended 100% intervention.

For seed 42 / 2500, exact values may vary only if the release changes, but the counterfactual defect rate and COPQ must be lower than baseline.

## 4 — Candidate intervention table

Expected:

- six candidate interventions are listed;
- **Recalibrate torque tool** carries the `RECOMMENDED` badge for seed 42;
- each row has target, evidence score, delta metrics, assumed cost and planned downtime.

## 5 — Partial intervention

Set:

- Intervention: `Recalibrate torque tool`
- Effectiveness: `50`
- Demand multiplier: `1.00`

Click **RUN WHAT-IF**.

Expected:

- counterfactual is recalculated;
- improvement is smaller than the 100% intervention;
- no page reload or server error.

## 6 — Demand stress

Keep the recommended intervention and set:

- Effectiveness: `100`
- Demand multiplier: `1.50`

Click **RUN WHAT-IF**.

Expected:

- queue / lead-time pressure should not improve simply because demand increased;
- metrics update while the intervention remains the same;
- demand multiplier is handled without NaN/Infinity/UI failure.

## 7 — Uncertainty statement

Expected after a what-if run:

- a paired bootstrap statement appears;
- it reports a 90% interval for defect-rate delta, COPQ delta and unit-flow-time delta;
- the page explicitly says simulation is not causal proof.

## 8 — Flow-fault stress scenario

Create a new run:

- Seed: `1`
- Units: `2500`

This deterministic blind seed should create the known queueing/changeover-style stress used in earlier acceptance testing.

Expected in the simulation section:

- a calibration/changeover intervention should be recommended;
- counterfactual queue wait and lead time should drop substantially.

## 9 — Reveal independence

On any run, review the simulation output, then click **REVEAL + SCORE**.

Expected:

- diagnosis scorecard appears;
- simulation results do not suddenly change because truth was revealed;
- simulation remains labeled as observable-evidence decision support.

## 10 — Existing validation still works

Enter `50` units and click **BREAK THE FACTORY**.

Expected readable message:

`Units must be a whole number between 100 and 250,000.`

No `[object Object]`.

## PASS rule

V0.6 is accepted when all ten tests behave as expected and no visible JavaScript/server error occurs.
