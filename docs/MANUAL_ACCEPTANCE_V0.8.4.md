# KAIZEN AI V0.8.4 — Evidence Namespace Hotfix Acceptance

You do **not** need to repeat the entire V0.8 test suite.

1. Fresh-extract `KAIZEN_AI_v0.8.4.zip`.
2. Copy your existing `.env` into the new folder. Keep your Gemini key private.
3. Confirm `GEMINI_MODEL=gemini-3.5-flash-lite` or leave the model setting at the supplied default.
4. Close every older KAIZEN terminal, then run `START_KAIZEN.bat`.
5. Confirm the health badge reads `OK / 0.8.4 · 20260815-v084-evidence1`.
6. Break the Factory with seed `42`, units `2500`. Keep ground truth sealed.
7. Ask exactly:

   `I have a $900 budget, maximum 8 hours downtime, and need at least 80 good units per hour. What should I do?`

### PASS criteria

- No popup saying fabricated/unknown IDs for `MACHINE_TORQUE_BIAS`, `GAGE_MEASUREMENT_DRIFT`, or `GAGE_RECALIBRATION`.
- Gemini returns a grounded answer.
- Function-call trace includes `solve_improvement_portfolio`.
- The answer explains that the hard constraints cannot be satisfied under the $900 budget (the modeled M2 recalibration costs more than the budget while no-action misses 80 good units/hour).
- Evidence chips, if shown, are real `EVD-####` ledger IDs only.
- Ground truth remains sealed and L5 causal confirmation remains locked.

8. Optional regression check: ask `Why do you suspect M2?` and confirm normal Ask KAIZEN still works.
