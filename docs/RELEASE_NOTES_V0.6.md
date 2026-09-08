# KAIZEN AI V0.6.0 — Process Simulation / What-If Lab

V0.6 preserves every accepted V0.1–V0.5 capability and adds a paired counterfactual process-simulation layer.

## New capability

KAIZEN can now take the blind Statistical Investigator's leading hypothesis and estimate what would happen under a specific engineering intervention while keeping the observed production mix fixed.

The simulation engine does **not** receive `scenario_code`, latent records, or sealed ground truth. Its inputs are:

- observable production records;
- incident boundary;
- statistical investigator output;
- user-selected intervention effectiveness;
- user-selected demand multiplier.

## Intervention library

- torque-tool recalibration;
- inspection-gage recalibration;
- fixture replacement + thermal stabilization;
- supplier-lot containment + humidity control;
- calibration sensor service;
- changeover standard-work / kit-layout restoration.

## Paired counterfactual replay

The same observed unit mix and deterministic release sequence are replayed before and after the intervention. This common-path design reduces irrelevant simulation noise and makes the difference between baseline and counterfactual easier to interpret.

Outputs include:

- defect rate / FPY;
- throughput and good throughput;
- lead time;
- queue wait;
- WIP;
- calibration service rate;
- COPQ per 1,000 units;
- torque Cpk;
- paired bootstrap 90% intervals for selected impact measures.

## Demand stress

The user can vary future demand from 0.50× to 1.75× the observed release pattern. Queueing is reconstructed from station service times and the single calibration resource rather than scaled heuristically.

## Causal guardrail

Simulation remains conditional on an observational hypothesis. It does **not** unlock the L5 intervention/DOE causal-confirmation gate.

## Validation

- 65 automated tests pass.
- 10/10 diagnostic checks pass.
- 18-case synthetic intervention benchmark passes 18/18 recommendation matches and 18/18 expected-domain improvements.
- Ground-truth reveal does not alter simulation output.
