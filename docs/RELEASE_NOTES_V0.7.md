# KAIZEN AI V0.7.0 — Improvement Portfolio Optimizer

## Added

- exact binary intervention-portfolio search over six actions (`2^6 = 64` possible portfolios)
- budget constraint
- maximum planned-downtime constraint
- minimum good-throughput constraint
- optional maximum-defect-rate constraint
- minimum observational-evidence gate for selected actions
- annual-volume financialization of modeled COPQ avoidance
- conservative evidence-adjusted value objective
- exact paired-replay validation of every non-pruned candidate portfolio
- deterministic paired bootstrap on the selected optimum
- feasible-portfolio ranking table
- explicit infeasible state when no portfolio satisfies all hard constraints
- optimizer API endpoints and UI controls
- V0.7 synthetic optimizer benchmark

## Guardrails

- sealed ground truth is not an optimizer input
- evidence scores are ranking indices, not probabilities
- evidence-adjustment is an explicit decision-risk heuristic
- throughput is not assigned an arbitrary dollar value
- optimizer output remains conditional on the observational diagnosis and counterfactual model
- causal / DOE confirmation remains locked

## Default decision problem

- Budget: $25,000
- Max downtime: 8.0 h
- Min good throughput: 80 units/h
- Max defect rate: 100% (inactive unless user tightens it)
- Annual volume: 200,000 units
- Effectiveness: 100%
- Demand multiplier: 1.00
- Min evidence score: 25/100
