# Industrial Engineering / Operations Research Methods in KAIZEN AI

This document lists the mathematical/engineering content actually implemented in the repository.

## Flow and capacity

### Takt

`Takt = available production time / customer demand`

The reference demand is expressed as seconds/unit and units/hour.

### Little's Law

`L = λW`

KAIZEN reconstructs launch-to-completion intervals from observed unit records and reports the closure error rather than merely displaying the formula.

### Empirical queueing

Arrival rate, release/service rate, queue wait, queue WIP, maximum queue and waiting probability are reconstructed from events. KAIZEN deliberately does not claim an M/M/1 model when the source data does not justify exponential/Poisson assumptions.

### Capacity

Station capacity is estimated from observed service times (`3600 / mean service seconds`) and compared with demand/release utilization. Bottlenecks are identified from the capacity profile.

### Line balance / value stream

Line efficiency, balance delay, smoothness, value-added time, necessary non-value-added time, pure wait and Process Cycle Efficiency are computed from the station definitions.

### OEE

`OEE = Availability × Performance × Quality`.

When an independent downtime-state stream is absent, availability is not inferred from utilization; the assumption is visibly flagged.

## Quality engineering / LSS

- Pareto / COPQ
- Cp, Cpk, Pp, Ppk
- I-MR control limits
- p-chart monitoring
- Gage R&R / ndc
- pre/post capability stratification

## Statistical investigation

- difference-in-differences;
- Welch t-test;
- Mann-Whitney U;
- two-proportion z-test;
- Pearson correlation;
- confidence intervals;
- Cohen's d / standardized effects / risk differences / rank-biserial effects;
- adjusted linear regression;
- logistic regression;
- factorial ANOVA with post-event interaction terms;
- explicit confounder checks.

Evidence is stored in a ledger and ranked. Evidence score is a ranking index, not a posterior probability.

## Counterfactual simulation

Candidate interventions replay the same observed unit mix under a modeled intervention transformation. Paired bootstrap intervals quantify model/sample uncertainty. Simulation is decision support and cannot unlock causal confirmation.

## Operations Research optimizer

### Decision problem

Candidate improvement actions are binary choices. Managerial constraints include:

`Σ cost_i x_i ≤ budget`

`Σ downtime_i x_i ≤ downtime cap`

with hard outcome feasibility on minimum good throughput and maximum defect rate after counterfactual evaluation.

### Current exact scale

Six binary actions imply 64 portfolios. KAIZEN evaluates the nonlinear counterfactual response for eligible portfolios.

### V1 MILP

Each evaluated portfolio becomes a binary selection variable `y_j`:

`maximize Σ NetValue_j y_j`

subject to:

`Σ y_j = 1`

`Σ Cost_j y_j ≤ B`

`Σ Downtime_j y_j ≤ D`

`Σ GoodThroughput_j y_j ≥ G_min`

`Σ DefectRate_j y_j ≤ Q_max`

`y_j ∈ {0,1}`

SciPy/HiGHS solves this binary MILP. Exhaustive enumeration independently validates the optimal objective/selection at the current tiny scale.

This exact precomputed-portfolio MILP is not claimed to solve the exponential scaling problem. A much larger intervention catalog would require an action-level surrogate/MILP, decomposition or a validated nonlinear formulation for interaction effects.

## DOE / causal validation

The DEMO experiment designer predeclares factor, levels, blocks, randomization, response and success criteria. The current synthetic gate requires correct direction, Welch `p < 0.01` and `|Cohen d| ≥ 0.8` before synthetic L5 can unlock.

## CONTROL

The V1 control engine specifies monitoring, reaction and benefits-verification policy but deliberately leaves realized benefits unverified until future observations exist.
