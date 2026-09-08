# KAIZEN AI V0.8.0 — Gemini Engineering Copilot

Build: `20260815-v080-gemini1`

## Added

- Google Gemini provider using the `google-genai` SDK.
- Gemini Interactions API manual function orchestration.
- Structured Pydantic response contract.
- `Ask KAIZEN` user interface.
- `Red Team My Recommendation` mode.
- Seven engineering tools exposing validated KAIZEN analytics without ground truth.
- Function-call trace in the UI.
- Evidence-ID validation: unknown/fabricated `EVD-xxxx` IDs are rejected server-side.
- Grounding enforcement: AI responses with no engineering tool call are rejected.
- AI status endpoint and safe unconfigured state.
- Local `.env` support while keeping `.env` ignored by Git.
- Gemini model override through `GEMINI_MODEL`.
- Optimizer payback formatting switches to days when below one month.

## AI boundary

The AI layer receives observable production evidence through callable tools only. It does not receive scenario codes, ground truth, latent variables, reveal-score truth or hidden fault strength.

The first Gemini turn is forced through `get_investigation_summary`. Subsequent tool use is model-selected. There is no callable reveal/ground-truth function.

## Causal policy

V0.8 may explain, synthesize, challenge and recommend based on the existing observational/simulation/optimization evidence. It may not unlock L5 intervention/DOE confirmation. AI agreement is not causal proof.

## Validation

- 80 automated tests pass.
- 13/13 diagnostics pass.
- JavaScript syntax check passes.
- Gemini function-call loop is contract-tested using a deterministic fake Interactions client.
- Ungrounded responses are rejected.
- Fabricated evidence IDs are rejected.
- AI tools are scanned for latent/ground-truth leakage.
- `/api/ai/status` does not expose secrets.
- AI endpoint safely returns 503 when the provider is not configured.

A live Gemini request is intentionally not part of the packaged automated suite because the release environment has no user's API key. Run the live acceptance tests locally after adding the key.
