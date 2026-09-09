# Kaizen AI deployment

Kaizen AI uses Render for the Python API and Vercel for the static control room. No secret is required for a working demo; the evidence-grounded fallback remains available without Gemini.

1. In Render, create a Blueprint from this repository. Keep the service name `kaizen-ai-api`; Render reads `render.yaml`, installs `requirements.txt`, starts `app.main:app`, and checks `/health`.
2. Confirm `https://kaizen-ai-api.onrender.com/health` returns `status: ok`.
3. In Vercel, import the same repository and leave Root Directory at the repository root. The checked-in `vercel.json` publishes `static/`.
4. Open the Vercel URL, run **Break the Factory**, and ask the copilot a question. The UI talks to the Render URL declared in `static/config.js`.
5. Optional: add `GEMINI_API_KEY` only in Render's secret environment settings. Never add it to Vercel or the repository.

If the Render service is renamed, update `static/config.js` before deploying Vercel.

## Why Vercel must never see the Python backend

Vercel's zero-config Python runtime auto-detects any `requirements.txt` /
`pyproject.toml` / `Pipfile` plus a matching entrypoint file (`app.py`,
`main.py`, etc., including the same names inside an `app/` or `src/` folder --
which matches this repo's `app/main.py`) and deploys the **whole repository**
as a Vercel Function that receives every request, regardless of `vercel.json`'s
`outputDirectory`. That is what broke production on 2026-09-09: the FastAPI app
ran on Vercel instead of a static file server, and the `/static/:path*` rewrite
(correct only for pure static hosting) stripped the `/static` prefix before the
request reached FastAPI, so every `/static/*` asset 404'd with FastAPI's own
`{"detail":"Not Found"}` even though the same app worked fine on Render.

The checked-in `.vercelignore` excludes `app/`, `requirements.txt`, and every
`kaizen_*` package so Vercel can never re-detect a Python entrypoint and will
always fall back to serving `static/` as plain files. **Do not add an `api/`
directory, a root-level `app.py`/`main.py`, or a `requirements.txt` that Vercel
can see** -- if the backend ever needs to run on Vercel too, use a separate
Vercel project (or Vercel Services) rather than exposing it from this one.
