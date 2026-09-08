# KAIZEN AI V0.4.1 — Patch Acceptance Tests

You do **not** need to repeat the full V0.4 acceptance pass. These checks target the attribution bug discovered during testing.

## 1. Version

Start `START_KAIZEN.bat`.

**PASS:** health badge shows `OK / 0.4.1`.

## 2. Seed 42 tool-drift regression

Create a blind run with:

- Seed: `42`
- Units: `2500`

Before revealing truth, scroll to Statistical Investigator.

**PASS:** leading suspect is **M2** / `Machine/tool bias centered on M2`, not M1.

Then reveal ground truth.

**PASS:** ground truth names **torque tool M2**, matching the investigator's affected asset while causal status remains observational/NOT CONFIRMED before reveal.

## 3. Reseal

Create another run.

**PASS:** ground truth is sealed again and investigator results are available without truth access.
