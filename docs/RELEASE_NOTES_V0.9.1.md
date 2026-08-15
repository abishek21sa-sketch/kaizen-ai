# KAIZEN AI V0.9.1 — New-Run Causal-State UI Reset

## Scope

V0.9.1 is a narrow UI/state-rendering hotfix. No statistical, simulation, optimizer, Gemini, active-investigation or DOE engine behavior changes.

## Fix

After a successful synthetic DOE, starting a new incident previously reset the L5 headline and metrics but could leave the prior experiment belief-revision sentence visible. This produced contradictory copy such as `L5 remains locked` beside a stale message saying the prior controlled experiment had met confirmation criteria.

V0.9.1 now:

- resets `beliefRevision` whenever a new run starts;
- defensively re-renders the pre-DOE causal-gate copy whenever an active overview has no experiment result;
- uses explicitly future-tense pre-DOE wording: an authorized experiment **may** unlock Level 5 only if it later satisfies every predeclared criterion;
- preserves the existing rule that observational probes cannot unlock Level 5.

## Validation

A dedicated regression verifies that the new-run reset contains the causal-gate copy and that an overview with no experiment result explicitly renders `No controlled experiment executed.` rather than stale DOE-success text.
