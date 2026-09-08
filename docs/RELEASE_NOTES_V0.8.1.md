# KAIZEN AI V0.8.1 — Gemini Live-Tool Hotfix

Build: `20260815-v081-gemini2`

## Reason for patch

V0.8.0 passed investigation/evidence/red-team Gemini calls, but a live optimizer-oriented prompt could produce an opaque local `HTTP 500`. The affected path was not exercised by the initial live tests.

The live Gemini model may populate optional function properties with JSON `null`. V0.8.0 directly converted optional values with `float(...)` / `int(...)`; a supplied null could therefore raise an uncaught `TypeError`. Google SDK/API exceptions were also not normalized by the local provider boundary, so some upstream failures could surface as an opaque 500.

## Fixes

- Optional tool values `null`/empty now mean "use KAIZEN default".
- Numeric/integer tool inputs are type-checked and range-checked centrally.
- Invalid model-selected tool arguments are returned to Gemini as a structured tool error so the model can correct and retry.
- Provider SDK/API exceptions are normalized to readable runtime errors and never expose API keys.
- One retry is performed for transient upstream 429/500/502/503/504-like failures.
- API endpoint now has a final AI error boundary and returns 502 instead of an opaque 500 for unexpected Gemini integration errors.
- Function results use strict JSON serialization (`allow_nan=False`).
- Gemini 3.x manual temperature override removed; low thinking level retained.
- New local port range: 9230–9264.

## Regression added

The specific prompt path is represented by automated coverage of an optimizer function call containing null optional fields:

`I have a $900 budget, maximum 8 hours downtime, and need at least 80 good units per hour. What should I do?`

V0.8.1 also tests that unexpected AI exceptions are surfaced as HTTP 502 rather than HTTP 500.
