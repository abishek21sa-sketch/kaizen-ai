# Frontend Demo Flow — KAIZEN AI

This product keeps its own visual language: **continuous-improvement A3 war room / evidence board**. The shared contract is behavioral evidence, not a shared layout or theme.

## Native entrypoint

`static/index.html`

## Project-specific demo sequence

1. break or import a factory case
2. measure SPC and flow
3. diagnose hypotheses
4. allocate experiments with CAPE-Loop
5. approve the control plan

## Evidence requirements

The screen must show the project-native inputs, objective, constraints, baseline/counterfactual, evidence class, signature decision, and human approval/hold state. The product must not imply autonomous actuation.

## API evidence surface

The read-only signature evidence endpoint is `/api/governance/signature`. Its response is linked to `artifacts/fortune50_capability_benchmark.json` and exposes the current decision, baseline, sensitivity/counterfactual evidence, and human-gated status.
