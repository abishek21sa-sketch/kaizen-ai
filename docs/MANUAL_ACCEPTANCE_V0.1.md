# KAIZEN AI V0.1 — Manual Acceptance

Perform these after extracting the release on the target Windows laptop.

1. **Clean startup** — Double-click `START_KAIZEN.bat`. Expected: diagnostics pass, browser opens, page title is `Hidden Factory V0.1`.
2. **Health indicator** — Expected top-right status: `● OK / 0.1.0`.
3. **Blind incident** — Leave Seed=`42`, Units=`2500`, click `BREAK THE FACTORY`. Expected: a `KZN-...` case ID appears and production metrics populate.
4. **Observable records** — Expected: table shows measured torque/alignment, queue time, machine/fixture, defects. It must NOT show actual torque, true defect, latent fault strength, or root cause.
5. **Ground-truth lock** — Before clicking reveal, the page must say the causal mechanism is sealed.
6. **Reveal** — Click `REVEAL GROUND TRUTH`, confirm. Expected: a specific causal mechanism and causal chain appears.
7. **Repeatability** — Click `BREAK THE FACTORY` again with Seed=`42`. Expected: a new case ID but the same generated incident behavior/data pattern for that seed.
8. **Different seed** — Change Seed to `43`, break again. Expected: different incident/data pattern.
9. **Input validation** — Set Units=`50`, click break. Expected: request is rejected; app must not silently generate an invalid run.
10. **API docs** — Visit `http://127.0.0.1:8000/docs`. Expected: FastAPI interactive docs load.

Report results as `1 PASS`, `2 PASS`, etc. For any failure, include the visible error or screenshot.
