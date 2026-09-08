# KAIZEN AI V0.5.0 — Manual Acceptance Tests

Use a fresh extraction of the V0.5 ZIP.

## Test 1 — Build identity

Run `START_KAIZEN.bat`.

Expected:
- page title says **Break the Factory Arena V0.5.0**;
- health badge says `OK / 0.5.0` and the V0.5 build ID;
- no BUILD MISMATCH banner.

## Test 2 — Blind reference incident

Use:
- Seed: `42`
- Units: `2500`

Click **BREAK THE FACTORY**.

Expected:
- incident loads;
- ground truth remains sealed;
- normal Six Sigma, IE and Statistical Investigator sections populate.

## Test 3 — Frozen arena prediction

Scroll to **BREAK THE FACTORY / INVESTIGATION ARENA**.

Expected before reveal:
- frozen prediction targets **M2**;
- direction is **INCREASE**;
- evidence score is populated;
- status is **STRONG SUSPECT**;
- timeline has six stages;
- final STOP stage is locked because observational evidence cannot confirm causality.

## Test 4 — Truth is still inaccessible

Before clicking Reveal + Score, confirm the Causal Firewall still says ground truth is sealed.

Expected:
- no root-cause text is visible;
- arena scorecard is hidden.

## Test 5 — Reveal + Score

Click **REVEAL + SCORE** and confirm.

Expected:
- truth says **Calibration bias developing in torque tool M2**;
- button changes to **DIAGNOSIS SCORED**;
- scorecard appears;
- attribution score is **100.0%**;
- dimensions show **4/4**;
- grade is **FULL ATTRIBUTION MATCH**;
- mechanism, target, direction and interaction checks are all green/pass.

## Test 6 — Investigator remains unchanged after reveal

After score/reveal, inspect the Statistical Investigator section.

Expected:
- leading suspect remains M2;
- it still says observational / STRONG SUSPECT rather than causal confirmation;
- L5 Intervention / DOE remains locked.

## Test 7 — New incident reseals truth and scorecard

Click **BREAK THE FACTORY** again.

Expected:
- new run ID;
- Causal Firewall returns to sealed;
- Reveal button returns to **REVEAL + SCORE**;
- previous scorecard disappears.

## Test 8 — Input validation regression

Set Units to `50` and click BREAK THE FACTORY.

Expected:
- readable message: `Units must be a whole number between 100 and 250,000.`
- no `[object Object]`.

If all eight pass, V0.5 can be accepted and locked.
