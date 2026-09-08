# KAIZEN AI V0.2 — Manual Acceptance Tests

Use the packaged ZIP on the target Windows laptop.

## Test 1 — Startup / version

- Double-click `START_KAIZEN.bat`.
- Expected: browser opens on a free 8765–8799 port.
- Expected header: `Lean Six Sigma Engine V0.2`.
- Expected health badge: `OK / 0.2.0`.

## Test 2 — Blind quality run

- Seed: `42`
- Units: `2500`
- Click `BREAK THE FACTORY`.
- Expected: incident loads, ground truth remains sealed, production table populates.
- Expected: DEFINE/MEASURE section populates automatically.

## Test 3 — Data-quality gate

- After Test 2, read `Data quality`.
- Expected: `100/100`.

## Test 4 — Pareto / COPQ

- Expected: defect-family Pareto bars appear.
- Expected: COPQ breakdown shows total, quality, flow-delay, rework, and scrap.
- No `[object Object]`, NaN, or blank-analysis errors.

## Test 5 — Capability

- Expected: capability table contains PRE and POST rows for Torque error and Alignment plus Adhesive strength by products A/B/C.
- Expected: Cpk/Ppk values are numeric where applicable.
- One-sided adhesive rows may show `—` for Cp/Pp while Cpk/Ppk remain populated.

## Test 6 — SPC

- Expected: torque-error SPC chart renders.
- Expected: CL/UCL/LCL are visible.
- Expected: an `INCIDENT` marker separates baseline from post-incident observations.
- Expected: signal count is numeric.

## Test 7 — MSA / Gage R&R

- Expected: Gage R&R percent and status appear.
- Expected: ndc appears.
- Expected: G1/G2 stratification table populates.

## Test 8 — Causal firewall

- Before reveal, quality analytics must be fully visible while ground truth remains sealed.
- Click `REVEAL GROUND TRUTH` only after inspecting the quality analysis.
- Expected: reveal succeeds and does not change/recompute quality metrics using hidden values.

## Test 9 — New run reseals truth

- After reveal, create another incident.
- Expected: button returns to `REVEAL GROUND TRUTH`; new incident is sealed.

## Test 10 — Validation

- Enter `50` units.
- Expected readable message: `Units must be a whole number between 100 and 250,000.`
