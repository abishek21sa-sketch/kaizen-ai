# KAIZEN AI V0.8.7 — Semantic Grounding Release

Build: `20260815-v087-semantic1`

## Fixed from the V0.8.6 live acceptance run

Three live behaviors were corrected:

1. **Optimizer prose contradiction** — Gemini could receive `INFEASIBLE` from the exact optimizer yet say the recalibration satisfied a `$900` budget. V0.8.7 makes the deterministic optimizer payload authoritative and rewrites the decision core from exact tool output.
2. **Missing ledger citations** — evidence questions could render `NO LEDGER IDS CITED` even though the Statistical Investigator had `EVD-####` rows. V0.8.7 backfills the current leading hypothesis's validated ledger IDs.
3. **Empty Red Team contradiction fields** — the prose could discuss confounding while the structured contradiction card said `None identified`. V0.8.7 merges the deterministic investigator's explicit contradictory evidence and confounder checks into the structured response.

## Tool routing

The first required Gemini tool is now task-aware:

- budget / downtime / throughput / portfolio decisions → `solve_improvement_portfolio`
- why / suspect / evidence / red-team questions → `get_diagnosis_evidence_packet`
- general engineering questions → `get_investigation_summary`

This reduces unnecessary model/tool turns and gives smaller Flash-Lite models a denser authoritative grounding packet.

## Guardrails retained

- Gemini 3.5 Flash-Lite primary model with quota fallback chain
- null-safe optional tool arguments
- bounded orchestration with forced final synthesis
- runtime-grounded engineering reference validation
- fabricated `EVD-####` rejection
- no sealed-ground-truth tool
- L5 causal confirmation locked
