# KAIZEN AI V0.4.1 — Asset Attribution Integrity Patch

## Why this patch exists

Target-laptop acceptance testing exposed an important statistical-interpretation defect in V0.4.0: for a two-level factor such as M1/M2, the difference-in-differences contrast is equal and opposite depending on which level is written as the target. V0.4.0 ranked by absolute DID magnitude, so it could identify the correct mechanism family while naming the unaffected complement asset.

For seed 42 / 2,500 units, the simulator truth was **M2 positive calibration bias**, while the V0.4.0 UI named **M1**.

## Fix

Asset attribution now requires both:

1. a strong differential DID signal, and
2. meaningful observed pre/post movement in the candidate asset itself.

The selection key is based on DID magnitude multiplied by the candidate level's own observed change. This uses observable production records only; scenario codes and latent truth remain unavailable to the investigator.

## Validation hardening

The benchmark now scores:

- mechanism family,
- affected target/asset,
- observed direction, and
- interaction partner where the modeled mechanism includes one.

Current deterministic synthetic benchmark: **36/36 full-attribution PASS** across 6 seeds × 6 fault families. This is a Hidden Factory benchmark only and is not a real-factory accuracy claim.

## Regression coverage

Added explicit tests ensuring:

- tool calibration drift is attributed to **M2**, not its equal-and-opposite M1 complement;
- gage measurement drift is attributed to **G2**;
- the seed-42 / 2,500-unit tool-drift case reports M2 with an increasing observed torque-error direction.
