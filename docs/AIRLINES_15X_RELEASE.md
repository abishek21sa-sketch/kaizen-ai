# KAIZEN AI — Airlines-1.5× Depth Candidate

Release: `KAIZEN_AI_FORTUNE50_AIRLINES15X_RC4`

## What changed

This release adds a provenance-aware empirical backbone, a live empirical API, project-native historical/entity diagnostics, a named empirical case study, external-source refresh/promotion workflow, live empirical charts, and a 26+ workspace contract in which each workspace has a distinct method/evidence/action definition.

## Current evidence mode

- Source: **Condition monitoring of hydraulic systems**
- Source URL: https://archive.ics.uci.edu/dataset/447/condition+monitoring+of+hydraulic+systems
- Mode: **offline_reference**
- Promotion state: **REFERENCE_ONLY**
- Local analyzable evidence: **600 rows / 32 fields**
- Workspaces: **26**

## Domain diagnostic

**factory incident evidence stratification**

Reference metrics:
```json
{
  "records": 600,
  "pre_defect_rate": 0.0067,
  "post_defect_rate": 0.1333,
  "defect_delta_pp": 12.667,
  "pre_mean_abs_torque_error": 0.3626,
  "post_mean_abs_torque_error": 0.6323
}
```

Decision signal: TRACE-LIFT should prioritize the discriminating probe for the strongest post-event equipment/measurement signal before CAPE allocates controlled experiments.

## Analytical chain

source provenance → schema/data-quality checks → entity/factor drilldown → cohort/history comparison → diagnostic ranking → predictive model → original algorithm → OR/simulation escalation → counterfactual challenge → human decision

## Windows gates

Core/offline acceptance:
```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\windows_airlines15x_acceptance.ps1
```

External-data promotion (internet required):
```powershell
.\scripts\windows_external_data_promotion.ps1
```

## Claim boundary

External-source results are claimed only when data_mode is refreshed_external or published_external_snapshot; offline_reference remains reference evidence.

The label “Airlines-1.5×” is an internal portfolio-depth target relative to the latest observable Airlines evidence, not an external company certification and not a claim that reference/synthetic data is real production evidence.
