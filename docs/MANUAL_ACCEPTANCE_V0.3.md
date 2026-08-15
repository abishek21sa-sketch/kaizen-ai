# KAIZEN AI V0.3 — Manual Acceptance Tests

Use the packaged ZIP on the target Windows laptop.

## Test 1 — Startup / version

- Double-click `START_KAIZEN.bat`.
- Expected: diagnostics pass and browser opens on a free 8765–8799 port.
- Expected header: `Lean Six Sigma + IE Engine V0.3`.
- Expected health badge: `OK / 0.3.0`.

## Test 2 — Blind run + causal firewall

- Seed `42`, Units `2500`, click `BREAK THE FACTORY`.
- Expected: quality and IE sections populate while ground truth remains sealed.

## Test 3 — IE headline metrics

- Expected Customer Takt: `45.0 s/unit`.
- Expected Post Throughput, Post Average WIP and Post Calibration OEE are numeric.
- No `NaN`, `[object Object]`, or blank cards.

## Test 4 — Flow / Little's Law

- PRE and POST rows appear.
- Throughput/h, good throughput/h, lead time and WIP are numeric.
- Little's Law error should display approximately `0.000000%` (floating rounding tolerance is acceptable).

## Test 5 — Queueing

- PRE and POST calibration rows appear.
- λ/h, μ/h, mean wait, Queue WIP, Max Queue and P(wait) are numeric.
- The note states empirical event reconstruction rather than an M/M/1 assumption.

## Test 6 — Capacity / bottleneck

- Seven PRE + seven POST station rows appear.
- Capacity/h and utilization values are populated.
- Bottleneck badge identifies PRE → POST station.
- Status pills show `AVAILABLE`, `AT RISK`, or `CAPACITY CONSTRAINED` as appropriate.

## Test 7 — Line balance

- Pre/Post efficiency, post cycle time and post smoothness are numeric.
- A takt-feasibility/balance-delay note is present.

## Test 8 — Value stream

- Pre/Post PCE are numeric.
- Post value-added and waiting time are numeric.
- The classification note explains transformation vs necessary NVA vs waiting.

## Test 9 — OEE honesty gate

- PRE and POST OEE rows populate.
- Availability = `100.00%` and status = `ASSUMED 100 PERCENT`.
- The note explicitly says no separate downtime-state stream exists; utilization must not be presented as Availability.

## Test 10 — Ground-truth independence

- Note headline quality/IE metrics.
- Reveal ground truth.
- Expected: existing analytical metrics do not change because reveal does not feed hidden values into the engines.

## Test 11 — New run reseals truth

- Create another incident after reveal.
- Expected: new incident is sealed and reveal button resets.

## Test 12 — Input validation

- Enter `50` units.
- Expected: readable whole-number/range error, never `[object Object]`.

## Optional stress demonstration — queueing fault

Use the API docs (`/docs`) to create a named `changeover_deterioration` scenario with seed 42 and 2500 units if you want to visibly stress the IE layer. The post calibration queue should increase dramatically, while the IE engine still has no access to the scenario truth before reveal.
