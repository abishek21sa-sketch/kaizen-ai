# KAIZEN AI V0.8.5 — Flash-Lite / Quota Resilience Hotfix

Build: `20260815-v085-orch1`

## Why this release exists

A real laptop acceptance run reached Google successfully but exhausted the free-tier quota for `gemini-3.6-flash` (HTTP 429). V0.8.5 treats this as a provider-capacity issue rather than an application failure.

## Changes

- Default Gemini model changed to stable `gemini-3.5-flash-lite`.
- Added configurable fallback chain through `GEMINI_FALLBACK_MODELS`.
- Default fallback chain: `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`, `gemini-2.5-flash-lite`.
- On HTTP 429 / quota exhaustion, KAIZEN immediately attempts the next configured model instead of pointlessly retrying the exhausted quota.
- Once a fallback succeeds, the same model is retained for the rest of that tool-orchestration request.
- The final AI response records the model that actually produced the answer.
- AI status now exposes the configured model chain but never the API key.
- Existing V0.8.1 null-argument and error-boundary fixes are retained.
- New local port range: 9270–9304.

## Engineering rationale

KAIZEN's deterministic Lean Six Sigma, IE, statistical, simulation and optimization engines perform the calculations. Gemini orchestrates tools, synthesizes evidence and explains/challenges decisions. A Flash-Lite model is therefore a better default for repeated career-fair/demo interactions where latency and quota headroom matter.

Model fallback does not alter the causal firewall. No Gemini model receives sealed factory ground truth, and L5 intervention/DOE confirmation remains locked.
