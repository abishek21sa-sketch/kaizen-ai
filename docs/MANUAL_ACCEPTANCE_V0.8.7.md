# KAIZEN AI V0.8.7 — Final Semantic Grounding Acceptance

You do **not** need to retest V0.1–V0.7.

1. Close every older KAIZEN terminal.
2. Fresh-extract `KAIZEN_AI_v0.8.7.zip`.
3. Copy your working `.env` into the new folder. Keep `GEMINI_MODEL=gemini-3.5-flash-lite`.
4. Run `START_KAIZEN.bat`.
5. Confirm `OK / 0.8.7 · 20260815-v087-semantic1` and a URL in the `9390–9424` range.
6. Break the Factory with **seed 42 / 2500 units**. Keep ground truth sealed.

## Test A — exact optimizer semantics

Ask:

> I have a $900 budget, maximum 8 hours downtime, and need at least 80 good units per hour. What should I do?

PASS if:

- no popup/error;
- tool trace contains `solve_improvement_portfolio`;
- the answer says the exact optimizer is **INFEASIBLE** / no feasible portfolio;
- it does **not** claim the `$1,250` torque-tool recalibration fits a `$900` budget;
- it identifies no-action/nearest modeled state as below the `80 good/h` floor.

## Test B — evidence citation grounding

Ask:

> Why do you suspect M2? Give me the strongest evidence and what still argues against it.

PASS if:

- evidence chips include real `EVD-####` IDs (for seed 42, normally `EVD-0001`, `EVD-0002`, `EVD-0003`);
- the answer still says M2 is observationally supported, not causally confirmed;
- contradictory evidence/limitations are not empty.

## Test C — Red Team consistency

Click **RED TEAM MY RECOMMENDATION**.

PASS if:

- response completes without popup/error;
- evidence IDs are present;
- `CONTRADICTORY EVIDENCE` is not `None identified` when investigator limitations/confounders exist;
- L5 remains locked / not causally confirmed.

If A, B and C pass, V0.8 is ready to lock.
