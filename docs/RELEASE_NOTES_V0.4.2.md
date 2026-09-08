# KAIZEN AI V0.4.2 — Build Synchronization Hardening

V0.4.2 retains the V0.4.1 direction-aware asset attribution fix and adds strict frontend/backend build synchronization.

## Why this patch exists
A laptop acceptance run showed a V0.4.1 page while `/health` still reported V0.4.0 and the investigator behaved like V0.4.0. That is a mixed-build condition, not an analytical failure of the patched package.

## Changes
- Centralized VERSION and BUILD_ID metadata.
- Root HTML is rendered with the active backend version/build.
- Browser assets are build-fingerprinted.
- Local responses use `Cache-Control: no-store`.
- UI blocks incident execution if frontend and backend build IDs differ.
- Launcher uses the visually distinct 8842–8876 port range for V0.4.2.
- V0.4.1 M2/G2 direction-aware attribution regression tests remain mandatory.

The causal firewall and L5 intervention/DOE confirmation gate are unchanged.
