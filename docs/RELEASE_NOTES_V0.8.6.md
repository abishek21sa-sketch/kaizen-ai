# KAIZEN AI V0.8.6 — Runtime Reference Grounding Hotfix

Build: `20260815-v086-ref1`

## Why this release exists
A real Gemini 3.5 Flash-Lite run correctly returned runtime asset identifiers `G1` and `M2` in the structured `engineering_references` field. V0.8.5 rejected them because its validator only recognized static hypothesis/intervention codes.

## Architectural fix
V0.8.6 replaces the static reference whitelist with a runtime-grounded catalog built only from observable or registered information:
- hypothesis codes, titles, targets and investigator attribution terms;
- intervention codes and registered intervention labels;
- machine, gage, fixture, supplier, supplier-lot, operator and product identifiers present in the current observable records;
- process stations and current line name.

References are canonicalized case-insensitively (`m2` -> `M2`). If a model accidentally places a valid runtime entity into `evidence_ids`, KAIZEN moves it to `engineering_references`. Only real current-ledger `EVD-####` tokens remain evidence citations.

## Guardrails retained
- fabricated or unknown `EVD-####` IDs are rejected;
- invented runtime assets such as `M99` are rejected;
- ground truth remains inaccessible to Gemini;
- L5 intervention/DOE confirmation remains locked;
- bounded tool orchestration and quota fallback remain active.

## Validation
- 98/98 automated tests passed in the development tree.
- 18/18 diagnostics passed.
- 36/36 blind full-attribution benchmark retained.
- 18/18 simulation recommendation/domain benchmark retained.
- 18/18 optimizer expected-action and hard-constraint benchmark retained.
- The exact live failure shape (`engineering_references=["G1", "M2"]`) is now a regression test.
