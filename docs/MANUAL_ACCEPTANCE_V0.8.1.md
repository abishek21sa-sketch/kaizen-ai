# KAIZEN AI V0.8.1 — Hotfix Acceptance

Use a fresh extraction of `KAIZEN_AI_v0.8.1.zip`. Do not overwrite V0.8.0.

## 1. Build sync

1. Close every old KAIZEN terminal window.
2. Start `START_KAIZEN.bat`.
3. Confirm the browser opens on port `9230` or the next free port.
4. Confirm the page says `Gemini Engineering Copilot V0.8.1`.
5. Confirm the health badge says `OK / 0.8.1 · 20260815-v081-gemini2`.
6. Copy your existing `.env` into this fresh folder or create it again locally. Never send the key.
7. Confirm `GEMINI READY` after restart.

## 2. Engineering setup

Break the Factory using seed `42`, units `2500`. Keep ground truth sealed.

## 3. Re-test successful AI paths

Ask:

`Why do you suspect M2? Give me the strongest evidence and what still argues against it.`

Then run `RED TEAM MY RECOMMENDATION`.

Both should return grounded answers and function-call traces.

## 4. Critical V0.8.1 regression

Ask exactly:

`I have a $900 budget, maximum 8 hours downtime, and need at least 80 good units per hour. What should I do?`

Expected:

- **no HTTP 500**;
- function trace includes `solve_improvement_portfolio`;
- answer explains that the modeled portfolio is infeasible under the $900 budget / 80 good-unit-per-hour floor, rather than inventing an expensive action;
- if Google itself returns a transient/API error, KAIZEN displays a readable `Gemini API request failed ...` message rather than a bare `HTTP 500`.

Then ask:

`Why is fixture replacement not preferred here?`

Expected: grounded comparison using evidence/simulation/optimizer tools; no opaque 500.

## Acceptance

V0.8.1 is accepted when the two prior Gemini paths still work and both optimizer-oriented questions complete without an opaque local HTTP 500.
