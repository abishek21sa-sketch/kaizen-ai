# KAIZEN AI V0.9.0 — Manual Acceptance

Use a fresh extraction. Close every older KAIZEN terminal first.

## A. Startup

1. Run `START_KAIZEN.bat`.
2. Confirm the browser opens on a port in `9430–9464`.
3. Confirm the header shows `Active Investigation Lab V0.9.0`.
4. Confirm health shows `OK / 0.9.0 · 20260815-v090-active1`.

## B. Strong-evidence active investigation

5. Run seed `42`, units `2500`.
6. In the V0.9 panel, confirm the uncertainty verdict is `STRONG SUSPECT`, not causal confirmation.
7. Confirm the recommended next measurement is a decision-relevant probe and a VOI score is shown.
8. Click `RUN NEXT PROBE`. Confirm a real effect, p-value and support score appear and the text explicitly says the probe remains observational.

## C. Human vs AI

9. Before reveal, choose one of the six diagnoses and click `LOCK MY DIAGNOSIS`.
10. Confirm the human choice becomes frozen.
11. Do not reveal yet. Confirm no Human-vs-AI score is shown before reveal.

## D. Experiment Designer / Level 5

12. Review the generated DOE: factor, levels, blocks/randomization, n and the predeclared p/effect rule must be visible.
13. Click `AUTHORIZE + RUN SYNTHETIC DOE` and confirm the browser asks for explicit authorization.
14. For seed 42 / 2500, the M2 recalibration DOE should pass and show `L5 UNLOCKED — SYNTHETIC DOE CONFIRMED`.
15. Confirm the experiment result shows control mean, treatment mean, delta, p-value and Cohen d.
16. Confirm the note says this is synthetic Hidden Factory causal confirmation, not real-world validation.

## E. Reveal + Human vs AI score

17. Click `REVEAL + SCORE`.
18. Confirm KAIZEN's normal arena score still works.
19. Confirm the V0.9 Human-vs-AI card now displays both human and AI scores.

## F. I DON'T KNOW regression

20. Start a new run with seed `0`, units `100`.
21. Confirm V0.9 says `I DON'T KNOW` rather than presenting the leading hypothesis as decision-ready certainty.
22. Confirm a next-measurement recommendation is still offered.

## G. Gemini optional checks

If Gemini is configured, ask:

- `What should we measure next to reduce uncertainty?`
- `Design a DOE to test the current leading diagnosis.`

The function trace should use the V0.9 planning tools. Gemini must not claim it executed or authorized the DOE.
