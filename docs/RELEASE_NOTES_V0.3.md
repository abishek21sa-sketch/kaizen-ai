# KAIZEN AI V0.3.0 — Industrial Engineering Engine

V0.3 extends the accepted V0.2 Lean Six Sigma layer with deterministic operations/flow analysis derived only from observable production records.

## Added

- Takt and required production rate with explicit schedule/demand assumptions.
- Reconstructed line lead time, throughput, good throughput, average/max WIP.
- Exact Little's Law closure checks.
- Calibration-cell empirical queue reconstruction and queue/cell WIP.
- Station capacity, demand utilization, release utilization and bottleneck ranking.
- Line balancing and smoothness metrics.
- Value-stream timing and Process Cycle Efficiency.
- Calibration-cell OEE diagnostic with explicit Availability assumption disclosure.
- `/api/runs/{run_id}/ie/overview` endpoint.
- IE dashboard sections in the browser UI.
- Reference-case tests and all-six-fault-family integration validation.

## Causal boundary

V0.3 may quantify where flow/capacity deteriorated. It may not infer *why*. The IE endpoint contains no latent simulator values, no root-cause labels and does not change after explicit ground-truth reveal.

## OEE design decision

The observable schema does not yet expose planned/unplanned downtime-state events. Availability is therefore held at 100% and flagged as an assumption. Utilization is not mislabeled as Availability. This is deliberate engineering conservatism.
