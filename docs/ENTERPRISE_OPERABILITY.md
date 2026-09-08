# Enterprise Operability & Decision Assurance

**Release:** `KAIZEN_AI_ENTERPRISE_RC2`  
**Phase:** Enterprise operability and decision assurance  
**Primary target:** Windows  

## Decision authority

The analytical engine may recommend, rank, simulate, or optimize, but this release does **not** grant autonomous production authority. The governing human authority is **Continuous-improvement engineer / experiment owner** and the execution mode is **EXPERIMENT_REVIEW_ONLY**.

## What this phase hardens

- Tamper-evident or hash-verifiable decision evidence.
- Explicit PASS/HOLD/review states instead of implicit action.
- Negative-path validation for malformed, unsafe, infeasible, weak-evidence, or tampered inputs.
- Request correlation / execution-boundary headers on decision APIs where an HTTP surface exists.
- A project-native enterprise-operability runner that exercises both the decision core and governance boundary.
- Regression evidence separated from native/polyglot or external-validation gates.

## Verified regression

- Passed: **128**
- Skipped in this environment: **0**
- Failures/errors: **0 / 0**
- Scope: Full current Python regression suite

## Windows enterprise gate

Run from a clean extraction in PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\\scripts\\windows_enterprise_acceptance.ps1
```

The Windows gate is intentionally stricter than the container evidence and must install/run project-native dependencies where applicable.

## Evidence boundary

Included numerical validation is deterministic/synthetic/model-based unless a source explicitly states otherwise. It must not be presented as real-factory, real-grid, real-vehicle-production, or clinical outcome validation.

## Gates still pending

- Real Windows PowerShell acceptance on target machine
- External/process-specific causal validation before operational intervention
