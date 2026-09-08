# KAIZEN AI v0.1.2

Frontend acceptance-test patch.

## Fixed
- Ground-truth button/state now resets correctly whenever a new blind incident is successfully created.
- Invalid unit/seed inputs now show a readable validation message instead of `[object Object]`.
- Failed run creation no longer overwrites the currently loaded incident's truth-state display.

## Validation
- Added UI regression tests for truth reset and error formatting.
