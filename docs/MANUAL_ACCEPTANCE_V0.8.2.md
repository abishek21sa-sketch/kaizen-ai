# KAIZEN AI V0.8.2 — Flash-Lite Acceptance

Use a fresh extraction of `KAIZEN_AI_v0.8.2.zip`.

## Setup

1. Close old KAIZEN terminal windows.
2. Extract V0.8.2 into a new folder.
3. Copy `.env.example` to `.env`.
4. Put your real key in `GEMINI_API_KEY=`. Do not share the key.
5. If copying an older `.env`, change `GEMINI_MODEL` to `gemini-3.5-flash-lite` or delete that line so the V0.8.2 default is used.
6. Start `START_KAIZEN.bat`.
7. Browser should open on port 9270 or the next free port.
8. Confirm `OK / 0.8.2 · 20260815-v082-lite1`.
9. Confirm AI model displays `gemini-3.5-flash-lite`.

## Live tests

Create seed 42 / 2500 and leave ground truth sealed.

### A — normal grounded question
`Why do you suspect M2? Give me the strongest evidence and what still argues against it.`

Expected: grounded answer, evidence IDs and function-call trace. No HTTP 429 from 3.6 Flash because 3.5 Flash-Lite is primary.

### B — Red Team
Click `RED TEAM MY RECOMMENDATION`.

Expected: grounded opposing analysis; L5 remains locked.

### C — optimizer tool path
`I have a $900 budget, maximum 8 hours downtime, and need at least 80 good units per hour. What should I do?`

Expected: function trace includes `solve_improvement_portfolio`; answer explains infeasibility under the modeled constraints rather than crashing.

## Fallback check (optional)

If an explicitly selected model is quota-exhausted, KAIZEN should try the next model listed in `GEMINI_FALLBACK_MODELS`. The answer card's model line must show the model that actually succeeded.
