# KAIZEN AI V0.8.4 — Gemini Evidence Namespace Hotfix

Build: `20260815-v084-evidence1`

## Why this release exists

A real laptop request using `gemini-3.5-flash-lite` reached Gemini successfully, but the structured response placed valid KAIZEN engineering codes in the `evidence_ids` field:

- `MACHINE_TORQUE_BIAS`
- `GAGE_MEASUREMENT_DRIFT`
- `GAGE_RECALIBRATION`

Those are legitimate hypothesis/intervention identifiers, but they are **not** evidence-ledger citations. V0.8.3 therefore rejected the response as if the values were fabricated evidence.

## Fix

V0.8.4 separates the namespaces:

- `evidence_ids`: only literal `EVD-####` statistical ledger identifiers;
- `engineering_references`: recognized KAIZEN hypothesis/intervention codes.

If Gemini misfiles a recognized engineering code inside `evidence_ids`, KAIZEN safely moves it into `engineering_references` instead of failing the entire answer.

Security/grounding remains strict:

- unknown/fabricated `EVD-####` IDs are rejected;
- arbitrary unknown engineering references are rejected;
- no sealed-ground-truth tool exists;
- L5 causal confirmation remains locked.

## Regression coverage

The live failure shape is reproduced offline with the exact `$900 budget / 8 h downtime / 80 good units per hour` optimizer path and misfiled codes.

Expected result: grounded answer accepted, real `EVD-####` citations retained, recognized KAIZEN codes normalized, optimizer tool trace preserved.
