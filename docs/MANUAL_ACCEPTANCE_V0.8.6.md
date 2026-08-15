# KAIZEN AI V0.8.6 — Final Gemini Grounding Acceptance

You do **not** need to retest V0.1–V0.7.

1. Close every older KAIZEN terminal.
2. Fresh-extract `KAIZEN_AI_v0.8.6.zip`.
3. Copy your working `.env` into the new folder. Keep `GEMINI_MODEL=gemini-3.5-flash-lite`.
4. Run `START_KAIZEN.bat`.
5. Confirm `OK / 0.8.6 · 20260815-v086-ref1` and a URL in the `9350–9384` range.
6. Break the Factory with seed `42`, units `2500`; keep truth sealed.
7. Ask exactly: `I have a $900 budget, maximum 8 hours downtime, and need at least 80 good units per hour. What should I do?`
   - PASS: a grounded answer renders; no unknown-reference popup; function trace includes `solve_improvement_portfolio`; answer explains the constraint set is infeasible under the modeled catalog.
8. Ask: `Why do you suspect M2? Give me the strongest evidence and what still argues against it.`
   - PASS: answer renders with real EVD citations and may reference runtime assets such as `M2`/`G1` without rejection.
9. Click `RED TEAM MY RECOMMENDATION`.
   - PASS: a grounded red-team answer renders and causal status remains not confirmed.

If these three Gemini operations pass, V0.8 is ready to lock.
