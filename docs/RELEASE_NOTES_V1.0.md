# KAIZEN AI V1.0 — Manufacturing Decision Intelligence

V1.0 is the unified product release built on the locked V0.9.1 engineering stack.

## Major changes

### Control-room UX
The former long-form page is preserved as multiple engineering workspaces instead of appearing as one continuous default scroll. Mission Control exposes the decision story in one screen; detailed Measure, Operations, Diagnose, Decide, Validate/Control and Data workspaces remain available from persistent navigation.

There is deliberately **one product interface**. The same Mission Control/workspace experience is used for normal engineering work, technical review and demonstrations.

### Manufacturing Data Contract v1.0
Adds explicit DEMO, FILE, REPLAY and LIVE source modes, conservative field mapping, schema/readiness reporting, CSV/JSON ingestion, live event sessions and historical replay APIs.

External data never receives synthetic ground truth. Synthetic reveal/scoring and synthetic DOE execution are blocked outside DEMO mode.

### Operations Research upgrade
The V0.7 exact enumeration remains as an independent nonlinear oracle for the six-action catalog. V1 also solves the portfolio choice as a binary MILP using SciPy/HiGHS over the counterfactually evaluated portfolio set. MILP/oracle agreement is explicitly reported.

### DMAIC CONTROL
Adds a deterministic control/benefits-verification plan with monitoring metric, reaction plan, stabilization window and reopen-analysis policy. Modeled benefits are never mislabeled as realized benefits.

### Engineering report / exports
Adds a printable deterministic run report, canonical CSV export, Mission Control JSON snapshot and replay event endpoint.

## Preserved constraints

- sealed causal truth in DEMO;
- no latent data in diagnostic engines;
- evidence score is not a probability;
- correlation/association cannot unlock L5;
- Gemini has no causal authority;
- optimizer output is model-conditional, not causal proof;
- external plant data is not assumed to contain missing signals;
- no realized savings are fabricated.

### V1.0 unified-interface cleanup
Mission Control and the seven workspaces are now the single canonical product experience. The internal `DEMO` source mode remains only as a technical data-source designation for the Hidden Factory and is displayed in the operational UI as `HIDDEN FACTORY`.
