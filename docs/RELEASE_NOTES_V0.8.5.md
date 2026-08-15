# KAIZEN AI V0.8.5 — Bounded Gemini Orchestration Hotfix

Build: `20260815-v085-orch1`

## Trigger

A live Gemini 3.5 Flash-Lite run on the question:

> I have a $900 budget, maximum 8 hours downtime, and need at least 80 good units per hour. What should I do?

reached KAIZEN's prior maximum tool-orchestration depth instead of returning a final answer.

## Root cause

The V0.8.4 provider kept exposing all engineering tools after every function result. Flash-Lite could therefore request additional or repeated tools indefinitely. The old safety mechanism stopped after ten rounds by raising an error, which protected the server but still failed the user's request and consumed unnecessary model quota.

## Fix

V0.8.5 implements bounded orchestration with forced synthesis:

- first turn remains grounded through `get_investigation_summary`;
- identical tool+argument calls are cached;
- repeated calls do not re-run deterministic engineering calculations;
- `solve_improvement_portfolio` is a terminal decision tool for a constraint question;
- duplicate-only rounds, four tool rounds, or seven unique tool calls close the tool phase;
- the continuation that performs final synthesis deliberately omits the `tools` parameter;
- prior function results remain available through `previous_interaction_id`;
- final structured output remains evidence-validated and causality-locked.

## Regression coverage

Two new live-protocol fixtures reproduce:

1. an optimizer call that would repeat indefinitely if tools remained exposed;
2. repeated identical evidence-ledger calls.

Both now terminate in a grounded final structured response. The optimizer failure case completes in three model interactions rather than reaching the old depth exception.
