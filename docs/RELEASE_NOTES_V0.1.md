# Release Notes — V0.1 Hidden Factory

**Status:** Engineering foundation / pre-AI

## Implemented
- Deterministic actuator-assembly event/data generator.
- Six fault families: fixture wear × temperature, supplier resin × humidity, torque-tool calibration drift, measurement-gage drift, calibration micro-stoppages, and changeover deterioration.
- Confounded operating assignments to prevent trivial root-cause discovery.
- Physical-vs-measurement separation.
- Queue formation at constrained calibration resource.
- Observable-vs-latent data separation and sealed truth boundary.
- Browser demo, FastAPI endpoints, CLI export, diagnostic script.

## Validation gate
- Automated tests must pass from a clean extracted release.
- Public APIs must not expose scenario code, physical truth, or latent fault variables before explicit reveal.
- Known fault families must produce the intended quality/flow signatures.

## Deferred by design
SPC, DMAIC analytics, IE metrics, root-cause inference, simulation experiments, optimization, Gemini, red-team AI, and career-fair mode are later releases.
