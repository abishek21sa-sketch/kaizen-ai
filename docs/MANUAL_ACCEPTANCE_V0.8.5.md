# KAIZEN AI V0.8.5 — Bounded Orchestration Acceptance

Only retest the Gemini path that failed in V0.8.4.

1. Close every older KAIZEN terminal.
2. Fresh-extract `KAIZEN_AI_v0.8.5.zip` into a new folder.
3. Copy your existing `.env` into the new folder. Keep your Gemini key private.
4. Confirm `GEMINI_MODEL=gemini-3.5-flash-lite` (or omit the model line to use the packaged default).
5. Run `START_KAIZEN.bat`.
6. Confirm the health badge is `OK / 0.8.5 · 20260815-v085-orch1` and the URL starts around `127.0.0.1:9310`.
7. Run seed `42`, units `2500`; keep ground truth sealed.
8. Ask exactly:
   `I have a $900 budget, maximum 8 hours downtime, and need at least 80 good units per hour. What should I do?`
9. PASS requirements:
   - no `maximum tool-orchestration depth` popup;
   - no HTTP 500;
   - answer completes;
   - function trace contains `get_investigation_summary` and `solve_improvement_portfolio`;
   - answer states the current constraint set is infeasible (the $900 budget cannot fund the modeled $1,250 torque-tool recalibration while no-action remains below 80 good units/hour);
   - causal status remains NOT CAUSALLY CONFIRMED / L5 locked.
10. Ask `Why do you suspect M2?` once. It should still complete normally.

If those two live Gemini questions complete, V0.8 can be locked.
