# KAIZEN AI V0.8.5 — Launcher Hotfix Acceptance

1. Fresh-extract `KAIZEN_AI_v0.8.5.zip`.
2. Copy/create `.env` with your existing Gemini key. Do not send the key to ChatGPT.
3. Double-click `START_KAIZEN.bat`.
4. The terminal must remain open and show diagnostics followed by `[START] ... (9270-9304)`.
5. Browser should open on `127.0.0.1:9270` or the next free port.
6. Confirm `OK / 0.8.5 · 20260815-v085-orch1`.
7. Run seed `42`, units `2500`.
8. Ask the `$900 budget / 8 h downtime / 80 good units per hour` question.
9. If Google quota is available, the answer must complete through a Gemini Lite model. If Google returns 429, KAIZEN should show the provider/quota error rather than an opaque local HTTP 500.

If startup itself fails for any reason, the terminal must stay open and show the exact error.
