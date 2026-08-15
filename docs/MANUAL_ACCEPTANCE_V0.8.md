# KAIZEN AI V0.8.0 — Manual Acceptance

Use a fresh extraction of `KAIZEN_AI_v0.8.0.zip`.

## A. Build and engineering regression

1. Close older KAIZEN terminal windows.
2. Double-click `START_KAIZEN.bat`.
3. Confirm the page opens on port `9180` or the next free port.
4. Confirm the header says `Gemini Engineering Copilot V0.8.0`.
5. Confirm the health badge says `OK / 0.8.0 · 20260815-v080-gemini1`.
6. Before configuring a key, the AI panel may correctly say `GEMINI NOT CONFIGURED`.
7. Break the Factory with seed `42`, units `2500`.
8. Confirm the accepted engineering spine still works and M2 remains the leading suspect.

## B. Configure Gemini locally

Do **not** send the key to ChatGPT.

1. In the extracted project folder, copy `.env.example` to a new file named `.env`.
2. Open `.env` in Notepad.
3. Set `GEMINI_API_KEY=YOUR_REAL_KEY`.
4. Save.
5. Close the KAIZEN command window completely.
6. Start `START_KAIZEN.bat` again.
7. Confirm the AI badge now says `GEMINI READY`.

If it does not, send the diagnostic/error text but never the key.

## C. Live Gemini grounding test

Use seed `42`, units `2500` and keep ground truth sealed.

Ask:

`Why do you suspect M2? Give me the strongest evidence and what still argues against it.`

Expected:

- a structured AI answer appears;
- the function-call trace contains at least `get_investigation_summary`;
- evidence IDs look like real `EVD-xxxx` ledger entries;
- the answer says observational support is not causal confirmation;
- ground truth is still sealed.

## D. Red-team test

Click `RED TEAM MY RECOMMENDATION`. The text box may be blank.

Expected:

- mode is `RED_TEAM`;
- the AI surfaces real contradictory/weakening evidence and assumptions;
- it does not simply reverse the diagnosis for dramatic effect;
- it recommends what evidence/intervention would reduce uncertainty;
- causal confirmation remains locked.

## E. Engineering tool-call test

Ask:

`I have a $900 budget, maximum 8 hours downtime, and need at least 80 good units per hour. What should I do?`

Expected:

- the trace should include the optimizer tool;
- KAIZEN should not invent a feasible expensive intervention;
- the explanation should distinguish infeasibility from uncertainty.

Then ask:

`Why is fixture replacement not preferred here?`

Expected:

- Gemini uses evidence/simulation/optimizer information rather than fabricating a comparison.

## F. Causal-firewall regression

1. Ask Gemini a question before reveal and note the response.
2. Reveal + Score.
3. Ask the same question again.

Expected:

- the AI may phrase the response differently because Gemini is generative, but its callable tools and evidence basis remain observable-only;
- the function trace contains no ground-truth/reveal tool;
- the UI continues to state that L5 confirmation is locked.

## Acceptance

V0.8 is accepted when A–F pass and at least one real Gemini answer plus one real Red Team answer execute successfully with the user's local API key.
