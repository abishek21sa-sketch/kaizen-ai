# KAIZEN AI V0.1.1 — Startup Reliability Patch

This patch addresses local port collisions observed during Windows acceptance testing.

## Changes

- Replaced the hard-coded port 8000 launcher with `scripts/launch.py`.
- KAIZEN now selects the first free port from 8765 through 8799.
- The browser opens only after the KAIZEN server is reachable.
- Added an automated regression test confirming `/` serves the KAIZEN UI.
- Updated application version to 0.1.1.

No simulator, causal-ground-truth, or public-record behavior changed.
