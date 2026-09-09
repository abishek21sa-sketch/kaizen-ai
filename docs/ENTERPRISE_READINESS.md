# Enterprise Readiness — KAIZEN AI

## Release status

**KAIZEN_AI_PORTFOLIO_RELEASE** is a portfolio release candidate, not a production deployment certification.

## Decision-system identity

Allocates scarce experiments under budget/downtime/run constraints while refusing to confuse observational priority with causal proof.

**Signature core:** CAPE-Loop experiment-allocation MILP + causal evidence firewall + improvement portfolio optimizer

## Verified in this recovery build

- 126/126 Python regression tests verified in two bounded groups (76 + 50)
- Machine-readable validation evidence is included and hashed.
- Production writes/autonomous execution are blocked by release governance.
- Windows remains the primary local acceptance target.

## Evidence inventory

- `docs/PORTFOLIO_VALIDATION.json` — SHA-256 `67b142e8e4c7392883dd56115cb9cbde25587657f50efbcbe3bf97deaf178d22`

## Gates still required before any production claim

- Windows PowerShell clean-environment acceptance
- External factory data/controlled experiment validation
- Configured external LLM provider gate when enabled

## Claim boundary

This repository may be presented as a reproducible engineering/research decision system supported by its included model-based evidence. It must not be presented as real-world production improvement, certification, clinical effectiveness, vehicle certification, grid approval, or plant/fab performance unless that external validation is subsequently completed.
