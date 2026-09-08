# KAIZEN AI V0.9.0 — Active Investigation + Causal Validation

## Release intent

V0.9 moves KAIZEN from "rank a suspect and recommend a modeled action" to a bounded investigation workflow that can explicitly abstain, buy information, compare a human against the AI, predeclare an experiment and revise beliefs after experimental evidence.

## New capabilities

### I DON'T KNOW policy

The V0.9 uncertainty controller uses the existing deterministic evidence score, top-to-second score gap and ambiguity label. It returns `I_DONT_KNOW`, `CAUTIOUS` or `STRONG_SUSPECT`. It does not convert the evidence score into a probability.

### Value-of-information ranking

Each of the six mechanism families has an observable follow-up probe with synthetic cost and time burden. The ranking is a transparent heuristic combining current decision relevance, discrimination between the top explanations, uncertainty and burden. It is not labeled as formal Bayesian or monetary EVSI/EVPI.

### Active observational probe

Executing a probe returns a test effect, p-value, support score and a transparent heuristic belief update. This layer never receives scenario code or ground truth and never unlocks Level 5.

### Human vs AI

A human selects one of the six current hypotheses before reveal. The prediction is frozen. After explicit reveal, human and AI are scored against the same mechanism/target/direction/interaction dimensions.

### Experiment Designer

The current leading observational hypothesis maps to a predeclared synthetic experiment with factor/levels, blocking, randomization, primary response, n=160 and a fixed success rule.

### Controlled synthetic DOE causal gate

Execution requires explicit `authorized=true`. Hidden Factory truth is used only to generate the controlled physical response. The output does not expose scenario code or ground truth.

Level 5 passes only when:

- improvement direction is correct;
- Welch two-sample p < 0.01; and
- |Cohen d| >= 0.8.

A wrong experiment remains locked and emits a belief-revision audit record.

### Gemini extension

Gemini may inspect the active-investigation plan and experiment design. It cannot execute the DOE, authorize it, reveal truth or bypass the predeclared gate.

## Validation

- 111/111 automated tests pass.
- 22/22 diagnostics pass.
- 18/18 correct DOE confirmations across six fault families × three seeds.
- deliberately wrong DOE regression remains unconfirmed.
- 18/18 reference human predictions score full attribution in the benchmark.
- deliberately small blind runs exercise the I DON'T KNOW policy.
- all retained V0.1–V0.8 benchmarks remain green.

All benchmark claims are synthetic Hidden Factory claims only.
