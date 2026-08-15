# KAIZEN AI V0.5.0 — Break the Factory Investigation Arena

## Added

- Blind Investigation Arena API and UI.
- Frozen prediction snapshot using observable records only.
- Six-stage investigation timeline: DETECT → MEASURE → HYPOTHESIZE → ADJUST → RANK → STOP.
- Explicit `POST /api/runs/{run_id}/arena/reveal-score` endpoint.
- Post-reveal scorecard comparing the blind prediction against sealed truth.
- Four score dimensions: mechanism family, affected target, direction, interaction partner.
- Synthetic benchmark harness at `scripts/benchmark_arena.py`.
- Arena reference tests and diagnostics.

## Causal firewall

The blind arena overview accepts only production records and the activation boundary. It receives no scenario code, latent records or ground truth. Scenario/ground-truth mappings are consulted only by the post-reveal scoring layer after explicit reveal.

Reveal does not alter the Statistical Investigator output.

## Causality policy

V0.5 still cannot claim causal confirmation. The L5 Intervention / DOE confirmation gate remains locked. A perfect reveal score means the blind diagnosis matched the simulator's known attribution, not that observational evidence has become causal proof.

## Validation

- automated tests pass;
- startup diagnostics pass;
- JS syntax passes;
- 36/36 current synthetic benchmark incidents pass full attribution.
