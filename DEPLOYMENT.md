# Kaizen AI deployment

Kaizen AI uses Render for the Python API and Vercel for the static control room. No secret is required for a working demo; the evidence-grounded fallback remains available without Gemini.

1. In Render, create a Blueprint from this repository. Keep the service name `kaizen-ai-api`; Render reads `render.yaml`, installs `requirements.txt`, starts `app.main:app`, and checks `/health`.
2. Confirm `https://kaizen-ai-api.onrender.com/health` returns `status: ok`.
3. In Vercel, import the same repository and leave Root Directory at the repository root. The checked-in `vercel.json` publishes `static/`.
4. Open the Vercel URL, run **Break the Factory**, and ask the copilot a question. The UI talks to the Render URL declared in `static/config.js`.
5. Optional: add `GEMINI_API_KEY` only in Render's secret environment settings. Never add it to Vercel or the repository.

If the Render service is renamed, update `static/config.js` before deploying Vercel.
