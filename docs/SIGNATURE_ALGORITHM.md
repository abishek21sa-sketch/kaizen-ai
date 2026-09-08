# CAPE-Loop — Signature Algorithm Contract

This document is the project-native mathematical center required by the portfolio governance pack. The implementation alias is **TRACE-LIFT experiment allocation**.

## Operational decision

The module makes one operational decision: **allocate a finite experiment budget across candidate process interventions**.

## Mathematical center

- **Decision variables:** integer replicate allocation per experiment candidate.
- **Objective:** maximize information value subject to budget, replicate, and balance constraints.
- **Constraints and release gates:** total cost <= budget; minimum and maximum replicates; balance tolerance across candidates.
- **Determinism:** the reference contract is deterministic for a fixed candidate set, scenario, and seed.
- **Solver status:** the current reference is an executable enumerative/closed-form contract; production solver integration remains downstream of this gate.

## Baseline and counterfactual

The named baseline is **rank-greedy allocation by value per cost**. The counterfactual is evaluated on the same inputs and scenario so that a claimed improvement cannot be caused by a changed data slice.

## Ablation

The declared ablation is to **remove the balanced-allocation constraint and retain budget bounds**. It is executable through the module's `ablation(...)` function and is covered by the signature tests.

## Sensitivity

The sensitivity sweep is: **vary the available budget multiplier and report allocation/value changes**. Sensitivity output is evidence about robustness, not a claim of causal production impact.

## Evidence classes and authority

Evidence is kept separate as observed, simulated, optimized, shadow-mode, and realized. **observed UCI hydraulic-system data for the process context; simulated experiment-allocation scenarios; no causal production claim** A human authority remains required before any operational action; autonomous execution is disabled.

## Implementation and acceptance

- Implementation: `kaizen_cape/signature_algorithm.py`
- Windows acceptance test: `tests/test_signature_algorithm.py`
- Required acceptance result: `4 tests, OK`, with invalid inputs and no-feasible cases controlled explicitly.

## Release boundary

This signature is release-ready only when this contract, the research-validation protocol, the machine-readable governance artifact, the existing Airlines 1.5x gates, and the final integrity/hash checks all pass together.
