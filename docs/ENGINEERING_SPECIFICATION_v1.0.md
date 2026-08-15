# KAIZEN AI — Engineering Specification v1.0

**Project:** KAIZEN AI — Autonomous Lean Six Sigma Decision Intelligence Platform  
**Governing status:** Approved build specification  
**Initial release:** V0.1 Hidden Factory  
**Target maturity:** 90–95% portfolio-production maturity without pretending to be plant-validated software.

---

## 1. Product thesis

KAIZEN AI converts manufacturing process data into an auditable continuous-improvement decision workflow:

**process evidence → problem detection → root-cause hypotheses → statistical challenge → improvement alternatives → simulation → constrained optimization → human approval → control → benefits verification.**

The system must demonstrate Lean Six Sigma knowledge, Industrial Engineering methods, software engineering, statistical quality engineering, operations research, simulation, machine learning where defensible, and Gemini-based generative reasoning without allowing the LLM to fabricate engineering evidence.

The core product question is:

> Given this process, what should be improved next, why, what evidence supports it, what alternative explanations remain, what will the intervention cost, what operational effect should be expected, and how will we know whether it actually worked?

---

## 2. Portfolio objective

KAIZEN AI is a flagship interactive project, not a generic analytics dashboard. Its recruiter-facing experience must be memorable, touchable, and defensible.

Signature experience:

1. **BREAK THE FACTORY** — inject a hidden industrial disturbance.
2. **DETECT** — observe statistically/operationally meaningful deterioration.
3. **INVESTIGATE** — generate and test competing causes.
4. **PROVE IT** — require statistical evidence before promoting a cause.
5. **RED TEAM ME** — attack the system's own conclusion.
6. **OPTIMIZE THE FIX** — choose interventions under budget/downtime/capacity constraints.
7. **SIMULATE IT** — compare baseline and proposed future behavior.
8. **REVEAL GROUND TRUTH** — score the diagnosis against the simulator's hidden causal mechanism.
9. **CONTROL** — monitor realized improvement.
10. **DMAIC AUTOPSY** — compare predicted benefit with actual benefit and reopen analysis when needed.

---

## 3. Concrete manufacturing environment

The reference process is a **precision electromechanical actuator assembly line** with product variants A/B/C.

Representative operations:

1. bearing press
2. motor assembly
3. adhesive dispense
4. torque fastening
5. calibration
6. functional test
7. final inspection
8. rework/scrap disposition

The process supports continuous CTQs, categorical defect outcomes, product mix, operator and machine assignment, supplier lots, fixtures, gages, environmental conditions, sequence effects, queues, bottlenecks, rework, scrap, maintenance-related deterioration, and measurable cost of poor quality.

---

## 4. Non-negotiable engineering principles

### 4.1 Deterministic engineering owns numerical truth

LLMs must not calculate or invent:

- Cp/Cpk/Pp/Ppk
- control limits
- p-values
- effect sizes
- confidence intervals
- regression coefficients
- optimization feasibility
- simulation outputs
- ROI/COPQ arithmetic
- MSA metrics

These come from validated deterministic code.

### 4.2 Gemini is an investigator, not the authority

Gemini may:

- generate plausible mechanisms;
- request approved analytical tools;
- synthesize returned evidence;
- compare competing explanations;
- propose next investigations;
- explain technical results in natural language;
- red-team a recommendation;
- draft evidence-linked FMEA/control-plan content.

Gemini may not self-certify a causal conclusion or bypass a failed evidence gate.

### 4.3 Correlation is not root cause

Predictive importance, correlation, and statistical significance are separate concepts. A variable may be predictive without being causal.

Root-cause promotion requires explicit evidence levels and contradictory-evidence checks.

### 4.4 The system must be allowed to say “inconclusive”

When evidence cannot distinguish credible explanations, the correct result is **INCONCLUSIVE**, followed by the highest-value next measurement or experiment.

### 4.5 Synthetic data must have hidden ground truth

Synthetic data is not used merely to produce attractive charts. The simulator contains causal mechanisms unavailable to the diagnostic layer. This allows benchmark scoring of root-cause discovery and intervention selection.

### 4.6 Evidence state must remain explicit

Capabilities and results are labeled as appropriate:

- Implemented
- Tested
- Validated
- Demo-ready
- Proposed

A file existing is not evidence that a feature works.

---

## 5. Causal firewall

The simulator has two separate data surfaces.

### 5.1 Observable production data

Examples:

- timestamp
- product variant
- operator/machine/fixture/gage IDs
- supplier and lot
- environmental readings
- measured CTQs
- station cycle times
- queue wait
- observed defects
- rework/scrap
- COPQ

This is the only surface accessible to diagnostic modules before a reveal.

### 5.2 Sealed latent data

Examples:

- physical “actual” CTQ values
- true defect status
- injected fault magnitude
- gage zero bias
- hidden micro-stop contribution
- excess changeover contribution
- causal mechanism and graph

This data exists only for benchmark scoring and explicit ground-truth reveal.

### 5.3 Leakage rule

No root-cause algorithm may import, query, join, or derive from the sealed latent store. Automated tests must detect accidental leakage through public APIs and observable schemas.

---

## 6. V0.1 hidden fault catalog

Initial incident families:

### F01 — Fixture wear × temperature

Progressive fixture F4 degradation increases alignment error; temperature amplifies torque variability. Operator O3 is deliberately scheduled on F4 more often, creating a plausible confounder.

### F02 — Supplier resin shift × humidity

A shifted S2 adhesive/resin lot reduces bond strength and interacts with high humidity. S2 is deliberately more common in certain temporal segments.

### F03 — Torque-tool calibration drift

Machine M2 develops a progressive positive torque bias. Product C is deliberately routed to M2 more often, creating product/machine confounding.

### F04 — Measurement-gage drift

Gage G2 develops a measurement offset while the physical process remains stable, producing false rejects/rework. This scenario tests whether future MSA logic can distinguish process deterioration from measurement-system failure.

### F05 — Calibration micro-stoppages

Intermittent sensor handshake delays reduce effective capacity, causing queue growth and lead-time deterioration without a matching quality shift.

### F06 — Changeover deterioration

Additional sequence-dependent setup time appears after product transitions, producing a capacity/schedule problem rather than a CTQ problem.

---

## 7. Lean Six Sigma functional scope

### DEFINE

- project charter
- problem statement
- business case
- goal statement
- scope
- VOC-to-CTQ mapping
- SIPOC
- Pareto
- COPQ baseline

### MEASURE

- operational definitions
- data-quality checks
- MSA
- Gage R&R
- repeatability/reproducibility
- capability baseline
- Cp/Cpk/Pp/Ppk
- defect/yield metrics
- stratification

### ANALYZE

- control-chart signals
- Pareto stratification
- Fishbone/6M hypothesis structure
- t tests/nonparametric tests where appropriate
- chi-square
- ANOVA
- regression/logistic regression
- interaction effects
- confidence intervals
- effect sizes
- FMEA evidence
- causal-confidence gate

### IMPROVE

- candidate intervention generation
- DOE planning/analysis
- what-if simulation
- operations-research intervention portfolio
- SMED and flow improvements where appropriate
- financial comparison

### CONTROL

- control plans
- reaction plans
- post-intervention SPC
- capability comparison
- benefit realization
- prediction-vs-actual tracking
- DMAIC autopsy/reopen logic

---

## 8. Industrial Engineering scope

The system must visibly use IE methods beyond generic analytics:

- takt time
- capacity analysis
- utilization
- throughput
- WIP
- Little’s Law checks
- bottleneck analysis
- line balancing
- queueing metrics
- value-stream metrics
- OEE
- discrete-event simulation
- constrained optimization
- cost/benefit analysis
- value of information
- decision analysis under uncertainty

---

## 9. Statistical evidence hierarchy

Candidate causes progress through evidence states:

- **L0 Observation** — descriptive anomaly only.
- **L1 Association** — reproducible statistical association.
- **L2 Material effect** — statistically and practically meaningful effect.
- **L3 Robustness** — survives relevant covariate/segment adjustment.
- **L4 Temporal/replication consistency** — holds across time/segments/replications.
- **L5 Intervention/DOE support** — controlled evidence or equivalent strong intervention evidence.

A “root cause” label must include its highest achieved evidence level, assumptions, contradictions, and missing evidence.

---

## 10. Evidence ledger

Every material conclusion receives an immutable logical record:

- recommendation ID
- timestamp
- dataset/run ID
- evidence IDs
- method/tool used
- parameters
- result
- confidence/evidence level
- assumptions
- contradictory evidence
- AI model/version if involved
- human approval state
- downstream action

No AI explanation may cite an analysis ID that does not exist.

---

## 11. AI architecture

Target AI integration uses the current Gemini API with tool/function calling and structured schemas.

Planned callable tools include:

- `get_process_capability`
- `get_spc_signals`
- `run_hypothesis_test`
- `run_regression`
- `run_anova`
- `segment_metric`
- `query_fmea`
- `calculate_copq`
- `run_queue_analysis`
- `simulate_intervention`
- `optimize_interventions`
- `get_evidence`

The model requests an operation; application code executes it; results return to the model for synthesis.

Secrets are loaded only from environment variables. `.env` must be ignored by version control. Gemini unavailability must not break deterministic engineering functions.

---

## 12. Root-cause investigator

The investigator must:

1. detect/receive an incident;
2. build candidate causes from data/process context;
3. request appropriate tests;
4. maintain supported/weak/rejected/inconclusive states;
5. search for contradictory evidence;
6. avoid operator-blame shortcuts;
7. separate measurement-system causes from process causes;
8. identify interactions where evidence supports them;
9. quantify uncertainty;
10. stop when evidence is insufficient;
11. propose the next information-gathering action when useful.

---

## 13. Red-team requirement

`RED TEAM MY RECOMMENDATION` must create a second-pass adversarial review that searches for:

- confounding
- missing variables
- measurement-system problems
- selection bias
- unstable estimates
- insufficient sample size
- model extrapolation
- simulation assumptions
- financial sensitivity
- operational infeasibility

The red-team pass may reduce confidence or reopen investigation.

---

## 14. Value-of-information requirement

When multiple explanations remain, KAIZEN may compare candidate measurements/experiments by:

- information gain / expected uncertainty reduction;
- monetary cost;
- downtime;
- labor burden;
- decision impact.

The objective is not “collect more data”; it is “collect the most decision-relevant information at reasonable cost.”

---

## 15. Simulation requirement

The future digital process simulation must model entities, constrained resources, queueing, setups/changeovers, rework/scrap, failures/micro-stops, and product mix.

Validation includes comparison against analytically tractable cases where possible and deterministic seeded regression cases.

---

## 16. Optimization requirement

Candidate improvements have attributes such as:

- implementation cost
- downtime
- labor requirement
- expected defect reduction
- expected capacity gain
- uncertainty/risk
- implementation prerequisites

The improvement portfolio optimizer selects actions subject to constraints such as budget, downtime, minimum throughput, staffing, and logical dependencies.

The solver output must include feasibility status and constraint utilization. Gemini explains the solution but never invents it.

---

## 17. Financial layer

At minimum:

- scrap cost
- rework cost
- inspection cost
- downtime/capacity loss
- implementation cost
- annualized benefit
- payback
- ROI
- sensitivity/uncertainty where supported

All assumptions must be visible.

---

## 18. Machine-learning scope

ML may be used for defect risk, CTQ prediction, anomaly detection, cycle-time prediction, or drift risk where it improves the system.

Rules:

- predictive feature importance is not causal evidence;
- holdout/validation design must be explicit;
- data leakage tests are required;
- baseline models are required;
- explainability must reference the predictive model, not claim root cause.

---

## 19. Unified Demonstration Workflow

The final recruiter workflow is a ~3-minute controlled demo:

1. landing question: “Can AI actually solve a manufacturing problem?”
2. BREAK THE FACTORY
3. live signal/detection timeline
4. investigation and competing hypotheses
5. evidence gate
6. red-team challenge
7. constrained intervention optimizer
8. simulation before/after
9. reveal hidden ground truth and diagnosis score
10. Ask KAIZEN follow-up

The mode must work reliably offline except for optional live Gemini calls; a deterministic scripted/demo fallback is required.

---

## 20. Human-vs-AI arena

A human participant can submit a suspected root cause and confidence before the system reveals its own answer. Both are scored against the hidden ground truth.

Metrics may include:

- root-cause Top-1 correctness
- causal interaction detection
- false-positive causes
- diagnosis time
- chosen intervention quality

This feature is for engagement and benchmarking, not a claim that AI broadly outperforms engineers.

---

## 21. Benchmark framework

Because synthetic ground truth is known, repeated blind incidents can measure:

- Top-1 root-cause accuracy
- Top-3 recall
- false-positive rate
- interaction-detection rate
- intervention-selection accuracy
- constraint-violation rate
- calibration of confidence
- diagnosis latency

Comparators should eventually include:

- descriptive/statistical baseline
- ML baseline
- Gemini-only reasoning baseline where safe to evaluate
- evidence-gated full KAIZEN system

Claims must be limited to the benchmark environment.

---

## 22. Target architecture

Final target:

```text
Browser / Career Fair UI
        |
FastAPI Application Layer
        |
+-------------------------------+
| Evidence / Workflow Orchestrator|
+-------------------------------+
    |        |        |       |
Stats/QA   IE/OR   Simulator   AI Investigator
    |        |        |       |
    +--------+--------+-------+
             |
      Observable Data Store

Sealed Ground-Truth Store  <-- benchmark/reveal only; no investigator access
```

V0.1 uses a lightweight static UI served by FastAPI to minimize bootstrap dependencies. A richer React/TypeScript interface is a later product/UI release after the analytical core stabilizes.

---

## 23. Release gates

### V0.1 — Hidden Factory

Required:

- deterministic observable records for fixed seed/scenario;
- six incident families;
- confounders;
- physical vs measurement separation;
- queueing behavior;
- causal firewall;
- sealed truth/reveal;
- API/browser demo;
- tests from clean extracted ZIP.

### V0.2 — Lean Six Sigma Engine

Required:

- DEFINE/MEASURE core;
- Pareto/COPQ;
- capability;
- SPC;
- MSA/Gage R&R;
- mathematical unit tests/reference cases.

### V0.3 — IE Engine

Required:

- OEE/takt/capacity/WIP/Little’s Law;
- bottleneck/line balance/queueing;
- reference-case validation.

### V0.4 — Statistical Investigator

Required:

- hypothesis-test router;
- regression/ANOVA/interactions;
- effect sizes/CIs;
- evidence hierarchy and ledger;
- no ground-truth access.

### V0.5 — Break the Factory Investigation Arena

Required:

- blind diagnosis flow;
- scored reveal;
- incident timeline;
- benchmark harness.

### V0.6 — Process Simulation

Required:

- intervention scenarios;
- DES/what-if model;
- validation against known cases.

### V0.7 — Improvement Optimizer

Required:

- constrained action portfolio;
- budget/downtime/capacity logic;
- feasibility and optimality/reference testing;
- financial layer.

### V0.8 — Gemini Investigator

Required:

- environment-key integration;
- tool calling;
- structured schemas;
- evidence-linked outputs;
- hallucination/evidence-ID tests;
- deterministic system survives AI outage.

### V0.9 — Advanced AI/Decision Features

Required:

- red team;
- inconclusive mode;
- value of information;
- human vs AI;
- DMAIC autopsy.

### V0.95 — Career Fair Product

Required:

- polished UI;
- 3-minute mode;
- robust demo scenarios;
- offline/demo fallback;
- recruiter-oriented explanations.

### V1.0 — Validated Portfolio Release

Required:

- complete regression suite;
- clean-install validation;
- documentation;
- architecture/evidence documentation;
- startup diagnostics;
- packaged ZIP tested after extraction;
- no unverified “production” claims.

---

## 24. V0.1 acceptance criteria

V0.1 is accepted only if all are true:

1. Fixed seed + fixed scenario produces identical observable records across runs.
2. Different incident families share the same pre-incident process for the same seed.
3. Observable records contain no latent physical truth or injected-fault labels.
4. Ground truth cannot be fetched through the API before explicit reveal.
5. Fixture-wear and supplier incidents produce material post-incident quality deterioration.
6. Gage drift produces a large observed-vs-true defect gap in the sealed benchmark store.
7. Micro-stops materially increase queue wait without requiring a quality shift.
8. Changeover deterioration occurs only on qualifying post-activation transitions.
9. Invalid inputs are rejected.
10. Browser UI can create a blind incident and reveal the truth explicitly.
11. Full automated test suite passes from the final extracted ZIP.
12. Startup diagnostics pass in the target environment after dependencies are installed.

---

## 25. Security and secrets

- Gemini keys are never committed.
- `.env` is ignored.
- Logs must not print API keys.
- Public demo data contains no proprietary information.
- No production-company branding/data is implied without permission.

---

## 26. Documentation/evidence policy

Every major module must document:

- purpose;
- inputs/outputs;
- assumptions;
- validation method;
- limitations;
- evidence state.

Synthetic results must be labeled synthetic. Later real-data validation, if performed, must be recorded separately rather than blended with synthetic validation.

---

## 27. Definition of project success

The project succeeds when a recruiter can interact with a technically credible system and the owner can explain:

- what DMAIC method is being used;
- what IE method is being used;
- what the statistics do and do not prove;
- why Gemini is useful;
- why Gemini is not trusted for numerical truth;
- how the hidden-ground-truth benchmark works;
- how improvement actions are constrained/optimized;
- how the system detects when its own recommendation failed.

The desired reaction is not merely “nice dashboard.” It is a substantive engineering conversation.

---

## 28. V0.4 implementation clarification

The V0.4 Statistical Investigator fulfills the release gate using an explicit hypothesis-test router rather than a single opaque model. Current implementation includes:

- difference-in-differences interaction screening;
- Welch / Mann-Whitney / proportion / Pearson tests;
- effect sizes and 95% confidence intervals where defensible;
- adjusted OLS regression with HC3 robust covariance;
- binomial logistic regression;
- factorial ANOVA;
- explicit post-event interaction terms;
- confounder checks;
- ranked evidence hierarchy and ledger.

The evidence score is non-probabilistic. V0.4 may identify a statistically strong suspect but cannot pass the Intervention / DOE confirmation gate. Causal confirmation therefore remains prohibited until a later intervention-capable release.

---

## Execution status — V0.6.0

The approved roadmap has reached the Process Simulation / What-If milestone. V0.6 implements paired counterfactual replay using observable records + Statistical Investigator output only. It does not consume scenario code, latent records or revealed ground truth. Intervention simulation remains conditional decision support and does not satisfy the L5 intervention/DOE causal-confirmation gate.

## Execution status — V0.7.0

V0.7 adds constrained improvement-portfolio optimization over the six existing modeled interventions. Decision variables are binary. With six actions, the entire `2^6` portfolio space is considered; portfolios that violate budget, downtime, or the minimum evidence gate are safely pruned before simulation, while all remaining portfolios are evaluated through paired counterfactual replay. The objective is evidence-adjusted first-year net COPQ value, with throughput retained as a hard constraint rather than arbitrarily monetized. The evidence discount is a transparent decision-risk heuristic and is not interpreted as a causal probability. Sealed ground truth remains unavailable to the optimizer, and L5 intervention/DOE causal confirmation remains locked.

---

## V0.8 Amendment — Gemini Engineering Copilot

The V0.8 AI layer is subordinate to the validated engineering system. Gemini may orchestrate analytical tools, synthesize evidence, explain recommendations and red-team conclusions, but may not replace deterministic/statistical calculation.

Mandatory AI controls:

1. Sealed simulator ground truth, scenario code and latent fields are not exposed as tools or prompt context.
2. The first model turn must call a KAIZEN engineering tool before a final response is accepted.
3. Final outputs use a structured schema containing evidence IDs, contradictory evidence, assumptions, unresolved questions, next actions and causal status.
4. Any cited evidence ID must exist in the current Statistical Investigator ledger; fabricated IDs cause server-side rejection.
5. No AI output may unlock L5 causal confirmation. Intervention/DOE evidence remains a separate later milestone.
6. The provider must degrade safely when no API key is configured; deterministic engineering features remain operational.
7. Secrets remain local in environment variables or `.env`, which is excluded from source control.

---

## Approved V0.9 extension — Active Investigation and Synthetic Causal Validation

The validated observational stack remains unchanged in authority. V0.9 adds a separate active-investigation layer with mandatory abstention when ambiguity is high, transparent next-measurement ranking, pre-reveal Human-vs-AI prediction freezing, predeclared controlled experiment design, explicit user authorization for experiment execution, and a synthetic Level-5 gate.

No observational probe, Gemini response, simulation result or optimizer result may unlock causal confirmation. Level 5 may pass only after an authorized controlled synthetic experiment meets its predeclared direction, significance and standardized-effect criteria. Hidden simulator truth may shape the controlled experimental response internally but must never be exposed as an input to the statistical investigator, Gemini, active observational probe or optimizer.

---

## V1.0 implemented release architecture (August 2026)

The V1.0.0 product release implements the specification through the following user-facing architecture:

- Control-room workspace navigation rather than one continuous default report page.
- Mission Control cross-engine decision snapshot.
- Career Fair guided demo mode.
- KAIZEN Manufacturing Data Contract v1.0 with DEMO / FILE / REPLAY / LIVE modes.
- CSV/JSON import and HTTP live-session ingestion boundary.
- External-data causal safeguard: no synthetic truth reveal/scoring or synthetic DOE execution.
- Binary MILP selection layer using SciPy/HiGHS plus the existing exhaustive nonlinear portfolio oracle at the six-action scale.
- Deterministic DMAIC CONTROL / benefits-verification plan.
- Printable deterministic engineering report and canonical CSV/JSON exports.

### Current deployment boundary

V1.0 is a portfolio-production manufacturing decision-intelligence system, not plant-certified controls software. FILE/REPLAY/LIVE support means the analytics core can consume mapped canonical events. Production-specific PLC/MES/SCADA/OPC-UA/MQTT/Kafka integrations remain adapter/deployment work and are not silently claimed as built-in connectors.

Real plant causal confirmation requires an intervention performed under plant governance outside KAIZEN. The synthetic Level-5 execution path remains DEMO-only.
