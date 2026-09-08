# KAIZEN AI V0.4.2 — Patch Acceptance

Use a **freshly extracted folder**. Do not merge this ZIP into an older KAIZEN folder.

1. Double-click `START_KAIZEN.bat`.
   - PASS: browser opens on port **8842** (or the next free port in 8842–8876).
   - PASS: header says `V0.4.2`.
   - PASS: health badge says `OK / 0.4.2 · 20260815-v042-sync1`.
   - FAIL: any `BUILD MISMATCH` banner.

2. Run Seed `42`, Units `2500` without revealing ground truth.
   - PASS: Statistical Investigator leading suspect is **M2**.
   - PASS: hypothesis title is `Machine/tool bias centered on M2`.
   - PASS: causal status remains `STRONG SUSPECT`, not confirmed root cause.

3. Reveal ground truth.
   - PASS: truth says `Calibration bias developing in torque tool M2`.
   - PASS: investigator remains M2 after reveal.

4. Run a new Seed `42`, Units `2500`.
   - PASS: truth reseals and investigator still independently identifies M2.

If all four pass, V0.4 Statistical Investigator is accepted and locked.
