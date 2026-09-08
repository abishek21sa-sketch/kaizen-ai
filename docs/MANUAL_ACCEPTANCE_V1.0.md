# KAIZEN AI V1.0 — Final Manual Acceptance

## A. Startup / control room

1. Start `START_KAIZEN.bat`.
2. Confirm `OK / 1.0.0 · 20260815-v100-public1` on a port in `9550–9589`.
3. Confirm the left navigation shows Mission Control, Measure, Operations, Diagnose, Decide, Validate and Data.
4. Confirm the application does not show all engineering panels in one endless default scroll.

## B. Unified product walkthrough

1. Confirm Mission Control is the normal entry point for every use case.
2. Seed `42`, Units `2500`, `BREAK THE FACTORY`.
3. Use the same persistent workspaces: Measure → Operations → Diagnose → Decide → Validate.
4. In Diagnose, freeze a Human-vs-AI guess before reveal.
5. In Decide, confirm simulation and `MILP portfolio selection + exhaustive nonlinear oracle` are visible.
6. In Validate, run an observational probe; L5 must remain locked.
7. Authorize the Hidden Factory synthetic DOE; the correct seed-42 design should unlock synthetic L5.
8. Open the CONTROL panel; `Benefits verified` must remain `NO` because no future stabilization data has been observed.
9. Return to Mission Control and reveal/score only after reviewing the blind diagnosis.

## C. Data architecture

1. Open Data.
2. Confirm DEMO / FILE / REPLAY / LIVE descriptions and the data-contract disclosure.
3. Import `examples/external_replay_seed42.csv` with boundary `252` (600-row example) in REPLAY mode.
4. Confirm the run loads and analytical workspaces populate.
5. Confirm reveal is disabled / no synthetic truth is available.
6. Confirm the synthetic DOE execute button is disabled for the external run.
7. Run `REPLAY SAMPLE`; event status should advance without changing source values.

## D. Report / exports

1. With any run loaded, open `ENGINEERING REPORT`.
2. Confirm report includes incident, KPIs, diagnosis, optimizer method, MILP/oracle agreement and causal status.
3. Confirm `EXPORT CANONICAL CSV` and `EXPORT SNAPSHOT JSON` respond.

## E. Regression commands

```bash
python -m pytest -q
python scripts/diagnose.py
python scripts/benchmark_v1.py
node --check static/app.js
```

Expected package release gate: 123 tests, 26 diagnostics, 18/18 V1 MILP/oracle benchmark agreement, 18/18 control-plan readiness and zero fabricated realized-benefit cases.
