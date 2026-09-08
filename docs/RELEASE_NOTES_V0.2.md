# KAIZEN AI V0.2.0 — Lean Six Sigma Engine

## Release gate

V0.2 implements the approved DEFINE/MEASURE core on top of the accepted V0.1 Hidden Factory.

## Added

- `kaizen_quality` deterministic analytical package.
- Dynamic project charter, VOC/CTQ, and SIPOC.
- Observable data-quality gate.
- Pareto and COPQ baseline.
- Cp/Cpk/Pp/Ppk capability analysis.
- I-MR and p-chart SPC calculations.
- Crossed Gage R&R and gage stratification.
- `/api/runs/{run_id}/quality/overview` endpoint.
- Browser sections for quality metrics, Pareto, capability, SPC, and MSA.
- Mathematical reference tests and causal-firewall API tests.

## Explicit boundary

V0.2 may identify statistical/process signals, but it may not label a root cause. It never reads sealed latent records or ground truth.
