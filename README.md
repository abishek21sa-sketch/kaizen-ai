## AIRLINES-1.5× DEPTH CANDIDATE

Current release `KAIZEN_AI_FORTUNE50_AIRLINES15X_RC4` adds a live empirical/historical analysis layer, 26+ substantive workspaces, project-native domain diagnostics, external-source refresh/provenance, and AI decisions grounded in explicit evidence mode. See `docs/AIRLINES_15X_RELEASE.md`.

# Fortune-50 TENX analytical release

**Internal portfolio target:** Math 10/10 · UI 10/10 · AI 10/10, subject to the evidence boundaries below.

- Repository-authored algorithm: **TRACE-LIFT-v1**
- Unique predictive-learning family: **LinUCB contextual-bandit learning**
- Analytical AI role: **AI Improvement Investigator**
- TENX workspaces: **20**
- Operational authority: **human-gated; autonomous execution blocked**

### Test the TENX layer on Windows

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\windows_tenx_acceptance.ps1
.\scripts\start_tenx_workstation.ps1
```

The first command validates prediction → decision → counterfactual → OR escalation → user-aid behavior and a five-seed originality stress suite. The second opens the dedicated analytical workstation.

> **Evidence boundary:** TENX bundled metrics are synthetic/reference validation, not field deployment validation. Existing native Windows, Julia/Go/Rust/frontend, external-data, clinical, or production gates remain applicable where documented.

---


## Portfolio RC1 — CAPE-Loop experiment governance

KAIZEN now includes CAPE-Loop, a binary MILP that allocates scarce investigative experiments across competing hypotheses under shared budget, downtime and run-capacity limits with diminishing information returns. The allocator can prioritize evidence generation but is structurally separated from the causal confirmation gate; observational evidence never authorizes causal claims or production writes.

# KAIZEN AI — Manufacturing Decision Intelligence V1.0

KAIZEN AI is an engineering decision-intelligence system that turns manufacturing production records into an auditable **DMAIC + Industrial Engineering + statistical investigation + simulation + operations-research decision workflow**. Gemini sits above deterministic engineering tools; it can explain and challenge evidence, but it cannot invent calculations or unlock causal confirmation.

V1.0 is the unified product release. It preserves the validated V0.1–V0.9.1 engines and adds a control-room UX, source-agnostic manufacturing data contract, FILE/REPLAY/LIVE ingestion paths, a formal MILP decision layer checked against an exact nonlinear oracle, printable engineering reports, and a deterministic CONTROL/benefits-verification plan.

## Signature flow

`BREAK THE FACTORY → MEASURE → FLOW → DIAGNOSE → DECIDE → VALIDATE → CONTROL`

1. **Break the Factory** — inject one of six sealed causal disturbances in DEMO mode.
2. **Measure** — Lean Six Sigma data quality, COPQ, Pareto, MSA, capability and SPC.
3. **Flow** — takt, throughput, good throughput, WIP, Little's Law, empirical queueing, capacity, bottlenecks, line balance, value stream and OEE diagnostics.
4. **Diagnose** — six competing mechanisms, difference-in-differences, adjusted regression, factorial ANOVA, confounder checks and evidence ledger.
5. **Decide** — paired counterfactual intervention replay plus constrained improvement portfolio optimization.
6. **Validate** — I DON'T KNOW policy, value of information, Human-vs-AI, active probes and predeclared controlled synthetic DOE.
7. **Control** — monitoring/reaction plan and benefits-verification rules that never mark modeled savings as realized savings.

## V1 control-room UX

The application is no longer one giant default scroll. The left navigation separates seven workspaces:

- Mission Control
- Measure
- Operations
- Diagnose
- Decide
- Validate / Control
- Data

**Mission Control** gives the whole decision story in one screen: defect deterioration, good throughput, leading diagnosis, decision state, MILP/oracle status and L5 causal status. The detailed engineering panels still exist, but they are opened only when needed.


## Data modes

V1 introduces the **KAIZEN Manufacturing Data Contract v1.0**.

### DEMO

The deterministic Hidden Factory. Sealed synthetic truth exists for blind benchmark scoring and authorized synthetic DOE.

### FILE

Upload a historical UTF-8 CSV or POST JSON records. Conservative aliases can map common plant names such as `equipment_id → machine_id` and `serial_number → unit_id`.

### REPLAY

Historical canonical records are emitted in original unit order for near-live demonstrations. Playback changes presentation speed only; source values are not modified.

### LIVE

Use the explicit HTTP session API:

```text
POST /api/live/sessions
POST /api/live/sessions/{session_id}/events
POST /api/live/sessions/{session_id}/finalize
```

Full-engine schema validation occurs before the live buffer becomes an analysis run.

### Real-world causal boundary

External FILE/REPLAY/LIVE data has **no synthetic ground truth**. KAIZEN blocks synthetic truth reveal and synthetic DOE execution on those runs. A real-world intervention must be authorized and executed outside KAIZEN; the resulting observations can then be ingested for evaluation.

KAIZEN therefore does **not** claim “any arbitrary factory CSV works automatically.” A source is supported after its fields are mapped into the canonical contract, and an analytical capability is only defensible when its required signals exist.

## Operations Research in V1

The intervention decision remains a binary constrained portfolio problem. For the current six candidate actions there are `2^6 = 64` possible portfolios.

V1 now uses two independent decision mechanisms:

1. **Binary MILP selection** over counterfactually evaluated candidate portfolios using SciPy/HiGHS.
2. **Exact nonlinear enumeration oracle** over the tiny 64-portfolio action space.

The MILP enforces:

- one selected portfolio;
- budget limit;
- planned downtime limit;
- minimum good-throughput requirement;
- maximum defect-rate requirement;
- evidence eligibility before candidate simulation.

The objective maximizes evidence-adjusted first-year modeled COPQ value minus one-time intervention cost. Throughput remains a hard constraint rather than being assigned a fabricated dollar value.

For the current catalog, the released recommendation uses the exact nonlinear oracle and reports whether the MILP agrees. This is intentionally conservative: precomputing all `2^n` portfolios is not presented as scalable to a large action catalog.

## Industrial Engineering / Lean Six Sigma mathematics

Implemented methods include:

- takt time;
- throughput and first-pass good throughput;
- Little's Law `L = λW` with explicit closure checks;
- empirical arrival/service/queue reconstruction without pretending M/M/1 assumptions;
- station capacity and utilization;
- bottleneck identification;
- line-balance efficiency, balance delay and smoothness;
- process-cycle efficiency/value-stream classification;
- OEE with explicit availability-data limitations;
- Cp/Cpk/Pp/Ppk;
- I-MR and p-chart monitoring;
- MSA / Gage R&R / ndc;
- Pareto and COPQ;
- difference-in-differences;
- Welch t-tests, two-proportion z-tests, Mann-Whitney U, Pearson correlation;
- confidence intervals and standardized effect sizes;
- adjusted regression, logistic regression and factorial ANOVA;
- randomized/predeclared DOE with direction, significance and effect-size gates;
- paired bootstrap counterfactual uncertainty;
- binary constrained portfolio optimization.

See `docs/IE_OR_METHODS.md` for equations and implementation notes.

## Gemini boundary

Gemini may ask KAIZEN tools for engineering evidence and synthesize the returned results. It may not:

- invent Cp/Cpk, p-values, effect sizes, queue metrics, simulation results or optimizer feasibility;
- reveal hidden scenario truth;
- authorize/execute the synthetic DOE;
- unlock L5;
- override deterministic optimizer facts.

Semantic grounding guards deterministic optimizer/evidence facts before an AI answer is shown.

## Causal boundary

Observation may support L0–L4. L5 requires intervention evidence.

In DEMO mode:

`blind diagnosis → predeclared DOE → explicit authorization → randomized controlled synthetic experiment → predeclared rule passes → synthetic L5 unlocked`

In external modes, synthetic L5 execution is disabled. A physical experiment occurs outside the application.

## CONTROL and benefits verification

V1 generates a deterministic control plan tied to the leading diagnosis. It includes:

- primary control metric;
- control method;
- baseline limits where available;
- monitoring cadence;
- owner role;
- reaction plan;
- minimum stabilization window;
- modeled target versus observed baseline;
- reopen-ANALYZE policy.

`realized_benefits_verified` remains false until real post-intervention observations exist. KAIZEN does not book simulated savings as realized savings.

## Engineering report and exports

For a loaded run:

- `GET /api/runs/{run_id}/report` — print/save a deterministic engineering report;
- `GET /api/runs/{run_id}/export/csv` — canonical observable records;
- `GET /api/runs/{run_id}/export/snapshot` — Mission Control JSON snapshot;
- `GET /api/runs/{run_id}/replay/events` — ordered replay events.

The report metrics are built from deterministic KAIZEN engines, not Gemini prose.

## Validation commands

```bash
python -m pytest -q
python scripts/diagnose.py
python scripts/benchmark_arena.py
python scripts/benchmark_simulation.py
python scripts/benchmark_optimizer.py
python scripts/benchmark_active.py
python scripts/benchmark_v1.py
node --check static/app.js
```

V1.0 release gate in this package:

- **123/123 automated tests**
- **26/26 diagnostics**
- Hidden Factory blind full attribution: **36/36**
- simulation recommendation/domain benchmark: **18/18**
- optimizer expected action + hard-constraint benchmark: **18/18**
- full-information synthetic DOE confirmation: **18/18**
- V1 MILP/exact nonlinear oracle agreement: **18/18**
- V1 control plan ready: **18/18**
- fabricated realized-benefit cases: **0/18**

All benchmark accuracy/confirmation counts are for the deterministic synthetic Hidden Factory only; they are not real-factory performance claims.

## Windows quick start

## Production deployment

KAIZEN is deployed as two independent services: the static control-room UI on
Vercel and the FastAPI engine on Render. The root `vercel.json` publishes the
`static/` directory; `render.yaml` starts the API on Render's assigned `$PORT`
and exposes `/health` for platform checks.

1. Create the Render Blueprint from this repository and set `KAIZEN_CORS_ORIGINS`
   to the final Vercel URL.
2. Create the Vercel project from the same repository. Vercel uses `static/` as
   its output directory and the UI defaults to
   `https://kaizen-ai-api.onrender.com` outside local development.
3. Set `GEMINI_API_KEY` only in Render if AI answers are required; never put it
   in the Vercel project.

The frontend and backend can be smoke-tested independently at `/` and `/health`
before connecting the two domains.

1. Extract the ZIP into a fresh writable folder.
2. Close older KAIZEN terminals.
3. Optional Gemini: copy `.env.example` to `.env`, add your local API key, and never commit/share it.
4. Double-click `START_KAIZEN.bat`.
5. V1.0 uses the first free local port in **9550–9589**.

For a concise walkthrough, stay in the normal product interface and move through **Mission Control → Measure → Operations → Diagnose → Decide → Validate**. There is no separate presentation mode.

## Enterprise operability gate

This source release includes a governed decision-assurance layer, negative-path operability tests, hash-verifiable evidence, and a Windows enterprise acceptance gate. See `docs/ENTERPRISE_OPERABILITY.md`.

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\\scripts\\windows_enterprise_acceptance.ps1
```


## Public Data Backbone
This release contains a structured public-data layer under `data/raw`, `data/processed`, `data/contracts`, `data/dictionaries`, `data/provenance`, and `data/snapshots`. Run `scripts\fetch_public_data_windows.ps1` when the primary public dataset is not bundled, then run `scripts\windows_real_data_acceptance.ps1`. `artifacts/data_backbone_status.json` records source state, row/feature counts, missingness, SHA-256, validation status, case-study state, claim boundary, model version, and the human decision authority.

The public-data case is `Hydraulic Degradation Investigation and Evidence Triage` and is wired into `TRACE-LIFT-v1` review. Missing external raw data never silently falls back to a real-data claim; the dossier explicitly enters `REFERENCE_MODE_HOLD_FOR_REAL_DATA_CLAIM`.
