from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import csv
import io
import uuid
import time
import os


from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from kaizen_factory.models import FactoryConfig
from kaizen_factory.registry import RunRegistry
from kaizen_factory.scenarios import FAULT_CATALOG
from kaizen_factory.simulator import simulate_factory
from kaizen_quality import build_quality_overview
from kaizen_ie import build_ie_overview
from kaizen_investigator import build_investigation_overview
from kaizen_arena import build_arena_overview, score_revealed_diagnosis
from kaizen_simulation import build_simulation_overview, run_what_if, INTERVENTION_CATALOG
from kaizen_optimizer import build_optimizer_overview, solve_improvement_portfolio
from kaizen_cape import build_cape_overview, allocate_experiment_portfolio, certify_cape_plan, verify_cape_certificate
from kaizen_cape.signature_algorithm import allocate_experiments as signature_allocate, ablation as signature_ablation, sensitivity as signature_sensitivity
from kaizen_ai import ask_kaizen, ai_status
from kaizen_data import contract_document, normalize_records, parse_csv_bytes, LiveSessionRegistry, build_external_result
from empirical.public_data_backbone import data_backbone_status
from kaizen_control import build_control_plan
from kaizen_active import (
    build_active_investigation_overview,
    execute_observational_probe,
    build_experiment_design,
    execute_controlled_experiment,
    freeze_human_prediction,
    score_human_prediction,
)
from .schemas import (
    RunCreate, RunCreated, WhatIfRequest, OptimizerRequest, AIAskRequest,
    ProbeRequest, HumanPredictionRequest, ExperimentExecuteRequest,
    ExternalDataRequest, LiveSessionCreateRequest, LiveEventsRequest, LiveFinalizeRequest,
)
from kaizen_version import VERSION, BUILD_ID

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
registry = RunRegistry()
human_predictions: dict[str, dict[str, Any]] = {}
experiment_results: dict[str, dict[str, Any]] = {}
active_probe_results: dict[str, dict[str, Any]] = {}
live_sessions = LiveSessionRegistry()
live_session_mappings: dict[str, dict[str, str]] = {}

app = FastAPI(
    title="KAIZEN AI — Manufacturing Decision Intelligence API",
    version=VERSION,
    description=(
        "V1.0 integrates Lean Six Sigma, Industrial Engineering, statistical diagnosis, simulation, "
        "MILP-backed decision optimization, uncertainty-aware investigation, controlled synthetic DOE, "
        "Gemini tool grounding and a source-agnostic manufacturing data contract."
    ),
)
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

_cors_origins_raw = os.getenv(
    "KAIZEN_CORS_ORIGINS",
    "http://localhost:9550,http://127.0.0.1:9550",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in _cors_origins_raw.split(",") if origin.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def prevent_local_build_cache(request, call_next):
    request_id=request.headers.get("X-Request-ID") or f"kzn-{uuid.uuid4().hex[:16]}"
    started=time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-Ms"] = f"{(time.perf_counter()-started)*1000:.3f}"
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["X-Kaizen-Version"] = VERSION
    response.headers["X-Kaizen-Build"] = BUILD_ID
    return response


@app.get("/", include_in_schema=False)
def index() -> HTMLResponse:
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    html = html.replace("__KAIZEN_VERSION__", VERSION).replace("__KAIZEN_BUILD_ID__", BUILD_ID)
    return HTMLResponse(html)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "kaizen-active-investigation",
        "version": VERSION,
        "build_id": BUILD_ID,
        "ai_enabled": ai_status()["configured"],
        "ai": ai_status(),
        "ie_enabled": True,
        "investigator_enabled": True,
        "arena_enabled": True,
        "simulation_enabled": True,
        "optimizer_enabled": True,
        "active_investigation_enabled": True,
        "human_vs_ai_enabled": True,
        "synthetic_doe_enabled": True,
        "data_modes": ["DEMO", "FILE", "REPLAY", "LIVE"],
        "manufacturing_data_contract": "1.0",
        "milp_optimizer_enabled": True,
        "control_plan_enabled": True,
        "cape_loop_enabled": True,
        "truth_boundary": "sealed until explicit reveal for DEMO; unavailable for external data",
    }


@app.get("/api/governance/signature")
def governance_signature() -> dict[str, Any]:
    """Expose the executable CAPE-Loop reference decision for the evidence UI."""
    values, costs, budget = [5, 1], [1, 1], 4
    selected = signature_allocate(values, costs, budget, max_replicates=4)
    baseline = signature_ablation(values, costs, budget, max_replicates=4)
    sensitivity = signature_sensitivity(values, costs, budget, multiplier=1.5, max_replicates=4)
    return {
        "status": "HUMAN_GATED_REFERENCE",
        "signature_algorithm": "CAPE-Loop",
        "decision": selected,
        "baseline": baseline,
        "sensitivity": sensitivity,
        "objective": "maximize information value under budget, replicate, and balance constraints",
        "counterfactual": "balanced-allocation ablation",
        "evidence_artifact": "artifacts/fortune50_capability_benchmark.json",
        "autonomous_execution": False,
    }


@app.get("/api/scenarios/public")
def public_scenarios() -> dict[str, Any]:
    # Deliberately excludes causal details and scenario codes to preserve blind-demo semantics.
    return {
        "count": len(FAULT_CATALOG),
        "fault_families": [
            "quality mean/variance shifts",
            "measurement-system failures",
            "supplier/material interactions",
            "capacity micro-stoppages",
            "sequence-dependent changeover loss",
        ],
        "note": "Break the Factory chooses the causal mechanism without revealing it.",
    }


@app.get("/api/data/contract")
def data_contract() -> dict[str, Any]:
    """Describe the canonical source-agnostic manufacturing data contract used by V1.0."""
    return {"version": VERSION, "build_id": BUILD_ID, "data_contract": contract_document()}


@app.get("/api/data/public-backbone")
def public_data_backbone() -> dict[str, Any]:
    """Expose read-only public-data evidence and model-selection provenance."""
    return data_backbone_status()


def _register_external_run(
    rows: list[dict[str, Any]], *, activation_unit: int, line_name: str,
    source_mode: str, mapping: dict[str, str] | None = None,
    source_metadata: dict[str, Any] | None = None,
) -> tuple[Any, dict[str, Any]]:
    try:
        records, mapping_report = normalize_records(rows, explicit_mapping=mapping or {}, require_full_engine=True)
        result = build_external_result(
            records,
            activation_unit=activation_unit,
            line_name=line_name,
            source_mode=source_mode,
            source_metadata=(source_metadata or {}) | {"mapping_report": mapping_report},
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    registry.put(result)
    human_predictions.pop(result.run_id, None)
    experiment_results.pop(result.run_id, None)
    active_probe_results.pop(result.run_id, None)
    return result, mapping_report


@app.post("/api/data/runs", status_code=201)
def create_external_data_run(payload: ExternalDataRequest) -> dict[str, Any]:
    """Create a FILE or REPLAY run from JSON records mapped into the KAIZEN contract."""
    result, report = _register_external_run(
        payload.records,
        activation_unit=payload.activation_unit,
        line_name=payload.line_name,
        source_mode=payload.source_mode,
        mapping=payload.mapping,
        source_metadata={"transport": "JSON"},
    )
    return {
        "run_id": result.run_id,
        "source_mode": result.source_mode,
        "units": result.config.units,
        "activation_unit": result.activation_unit,
        "mapping_report": report,
        "ground_truth_available": False,
        "message": "External observable data accepted. Synthetic truth reveal and synthetic DOE execution are disabled for this run.",
    }


@app.post("/api/data/import/csv", status_code=201)
async def import_csv_run(
    file: UploadFile = File(...),
    activation_unit: int = Form(...),
    line_name: str = Form("External Manufacturing Line"),
    source_mode: str = Form("FILE"),
    mapping_json: str = Form("{}"),
) -> dict[str, Any]:
    """Import a UTF-8 CSV into FILE/REPLAY mode using explicit or conservative alias mapping."""
    try:
        mapping = json.loads(mapping_json or "{}")
        if not isinstance(mapping, dict):
            raise ValueError("mapping_json must be a JSON object")
        rows = parse_csv_bytes(await file.read())
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    result, report = _register_external_run(
        rows,
        activation_unit=activation_unit,
        line_name=line_name,
        source_mode=source_mode.upper(),
        mapping=mapping,
        source_metadata={"transport": "CSV", "filename": file.filename or "uploaded.csv"},
    )
    return {
        "run_id": result.run_id,
        "source_mode": result.source_mode,
        "units": result.config.units,
        "activation_unit": result.activation_unit,
        "mapping_report": report,
        "ground_truth_available": False,
    }


@app.post("/api/live/sessions", status_code=201)
def create_live_session(payload: LiveSessionCreateRequest) -> dict[str, Any]:
    session = live_sessions.create(payload.line_name, payload.activation_unit)
    live_session_mappings[session.session_id] = dict(payload.mapping)
    return {
        "session_id": session.session_id,
        "source_mode": "LIVE",
        "line_name": session.line_name,
        "created_at": session.created_at,
        "state": "COLLECTING",
        "contract_url": "/api/data/contract",
    }


@app.post("/api/live/sessions/{session_id}/events")
def append_live_events(session_id: str, payload: LiveEventsRequest) -> dict[str, Any]:
    try:
        session = live_sessions.append(session_id, payload.records)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "session_id": session_id,
        "state": "COLLECTING",
        "accepted_this_request": len(payload.records),
        "buffered_records": len(session.records),
        "note": "Events remain raw until finalize; full-engine schema validation occurs before an analysis run is created.",
    }


@app.post("/api/live/sessions/{session_id}/finalize", status_code=201)
def finalize_live_session(session_id: str, payload: LiveFinalizeRequest) -> dict[str, Any]:
    try:
        session = live_sessions.get(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    activation_unit = payload.activation_unit or session.activation_unit or int(round(len(session.records) * 0.42))
    result, report = _register_external_run(
        session.records,
        activation_unit=activation_unit,
        line_name=session.line_name,
        source_mode="LIVE",
        mapping=live_session_mappings.get(session_id, {}),
        source_metadata={"transport": "LIVE_HTTP_EVENT_BUFFER", "live_session_id": session_id},
    )
    try:
        live_sessions.finalize(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "session_id": session_id,
        "run_id": result.run_id,
        "source_mode": "LIVE",
        "units": result.config.units,
        "activation_unit": result.activation_unit,
        "mapping_report": report,
        "ground_truth_available": False,
        "state": "FINALIZED",
    }


@app.post("/api/runs", response_model=RunCreated, status_code=201)
def create_run(payload: RunCreate) -> RunCreated:
    if payload.scenario != "random" and payload.scenario not in FAULT_CATALOG:
        raise HTTPException(status_code=422, detail="Unknown scenario. Use 'random' for blind mode.")
    config = FactoryConfig(
        seed=payload.seed,
        units=payload.units,
        activation_fraction=payload.activation_fraction,
    )
    result = simulate_factory(config, payload.scenario, reveal_truth=True)
    registry.put(result)
    human_predictions.pop(result.run_id, None)
    experiment_results.pop(result.run_id, None)
    active_probe_results.pop(result.run_id, None)
    return RunCreated(
        run_id=result.run_id,
        units=result.config.units,
        activation_unit=result.activation_unit,
        symptom=result.public_summary["symptom"],
        affected_step_hint=result.public_summary["affected_step_hint"],
    )


@app.get("/api/runs")
def list_runs() -> list[dict[str, Any]]:
    return registry.list_public()


@app.get("/api/runs/{run_id}/summary")
def run_summary(run_id: str) -> dict[str, Any]:
    try:
        stored = registry.get(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    result = stored.result
    return {
        "run_id": run_id,
        "line_name": result.config.line_name,
        "units": result.config.units,
        "activation_unit": result.activation_unit,
        "public_summary": result.public_summary,
        "truth_revealed": stored.revealed,
        "source_mode": result.source_mode,
        "source_metadata": result.source_metadata,
    }


@app.get("/api/runs/{run_id}/records")
def run_records(
    run_id: str,
    limit: int = Query(default=250, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    try:
        stored = registry.get(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    records = stored.result.records
    return {
        "run_id": run_id,
        "total": len(records),
        "offset": offset,
        "limit": limit,
        "records": records[offset : offset + limit],
    }

@app.get("/api/runs/{run_id}/mission-control")
def mission_control(run_id: str) -> dict[str, Any]:
    """Return one compact cross-engine decision snapshot for the V1.0 control-room UI."""
    try:
        stored = registry.get(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    result = stored.result
    q = build_quality_overview(result.records, result.activation_unit, line_name=result.config.line_name, seed=result.config.seed)
    ie = build_ie_overview(result.records, result.activation_unit)
    inv = build_investigation_overview(result.records, result.activation_unit)
    sim = build_simulation_overview(result.records, result.activation_unit)
    opt = build_optimizer_overview(result.records, result.activation_unit)
    active = build_active_investigation_overview(result.records, result.activation_unit)
    control = build_control_plan(result.records, result.activation_unit, line_name=result.config.line_name, seed=result.config.seed)
    if run_id in experiment_results:
        active["experiment_result"] = experiment_results[run_id]
        active["causal_confirmation"] = {
            "level_5": "UNLOCKED" if experiment_results[run_id]["causal_confirmation"]["passed"] else "LOCKED",
            **experiment_results[run_id]["causal_confirmation"],
        }
    pre = result.public_summary["pre_incident"]
    post = result.public_summary["post_incident"]
    top = inv["ranked_hypotheses"][0]
    rec = sim.get("recommended_intervention") or {}
    best = opt.get("best_portfolio")
    return {
        "run_id": run_id,
        "version": VERSION,
        "build_id": BUILD_ID,
        "source_mode": result.source_mode,
        "truth_revealed": stored.revealed,
        "incident": {
            "symptom": result.public_summary.get("symptom"),
            "activation_unit": result.activation_unit,
            "units": result.config.units,
            "line_name": result.config.line_name,
        },
        "kpis": {
            "pre_defect_rate": pre["observed_defect_rate"],
            "post_defect_rate": post["observed_defect_rate"],
            "post_good_throughput_uph": ie["flow"]["post"]["good_throughput_units_per_hour"],
            "post_lead_time_s": ie["flow"]["post"]["mean_flow_time_s"],
            "post_wip": ie["flow"]["post"]["average_wip_units"],
            "copq_per_1000_usd": q["pareto_copq"]["copq"]["per_1000_units_usd"],
        },
        "diagnosis": {
            "hypothesis_code": top["code"],
            "title": top["title"],
            "target": top["target"],
            "evidence_score": top["evidence_score"],
            "status": top["status"],
            "ambiguity": inv["ambiguity"]["level"],
        },
        "decision": {
            "recommended_intervention": rec.get("label"),
            "recommended_target": rec.get("diagnostic_basis", {}).get("target"),
            "optimizer_status": opt["solver"]["status"],
            "optimizer_method": opt["solver"]["method"],
            "milp_oracle_agreement": opt["solver"].get("oracle_agreement"),
            "best_portfolio_labels": [x["label"] for x in best.get("interventions", [])] if best else [],
            "first_year_net_value_usd": opt.get("best_financials", {}).get("first_year_net_value_usd") if opt.get("best_financials") else None,
        },
        "validation": {
            "uncertainty_verdict": active["uncertainty"]["state"],
            "best_next_measurement": active["value_of_information"]["ranked_candidates"][0]["label"],
            "l5": active.get("causal_confirmation", {}).get("level_5", "LOCKED"),
            "synthetic_doe_available": result.source_mode == "DEMO",
            "control_plan_state": control["state"],
            "control_primary_metric": control["monitoring"]["primary_metric"],
        },
        "causal_policy": "Gemini and observational analytics cannot unlock L5. DEMO mode requires an authorized predeclared synthetic DOE; external modes require a real-world intervention performed outside KAIZEN.",
    }


@app.get("/api/runs/{run_id}/replay/manifest")
def replay_manifest(run_id: str) -> dict[str, Any]:
    try:
        stored = registry.get(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    r = stored.result
    return {
        "run_id": run_id,
        "source_mode": r.source_mode,
        "events": len(r.records),
        "activation_unit": r.activation_unit,
        "ordering": "unit_index",
        "policy": "Replay emits the canonical historical sequence without changing values. UI playback speed changes wall-clock presentation only.",
    }


@app.get("/api/runs/{run_id}/replay/events")
def replay_events(
    run_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=5000),
) -> dict[str, Any]:
    try:
        stored = registry.get(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    rows = stored.result.records[offset:offset + limit]
    return {
        "run_id": run_id,
        "offset": offset,
        "limit": limit,
        "total": len(stored.result.records),
        "events": rows,
        "next_offset": offset + len(rows) if offset + len(rows) < len(stored.result.records) else None,
    }


@app.get("/api/runs/{run_id}/export/csv")
def export_run_csv(run_id: str):
    try:
        stored = registry.get(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    rows = stored.result.records
    stream = io.StringIO()
    if rows:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    data = stream.getvalue().encode("utf-8")
    return StreamingResponse(
        io.BytesIO(data),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{run_id}_kaizen_records.csv"'},
    )


@app.get("/api/runs/{run_id}/export/snapshot")
def export_run_snapshot(run_id: str) -> JSONResponse:
    snapshot = mission_control(run_id)
    return JSONResponse(snapshot, headers={"Content-Disposition": f'attachment; filename="{run_id}_kaizen_snapshot.json"'})


def _report_html(run_id: str) -> str:
    snap = mission_control(run_id)
    k = snap["kpis"]
    d = snap["diagnosis"]
    dec = snap["decision"]
    val = snap["validation"]
    def esc(v: Any) -> str:
        import html
        return html.escape("—" if v is None else str(v))
    defect_delta = 100 * (float(k["post_defect_rate"]) - float(k["pre_defect_rate"]))
    value = ('$' + format(float(dec['first_year_net_value_usd']), ',.0f')) if dec['first_year_net_value_usd'] is not None else '—'
    return f'''<!doctype html><html><head><meta charset="utf-8"><title>KAIZEN Engineering Report — {esc(run_id)}</title>
<style>body{{font-family:Arial,sans-serif;color:#17211d;margin:40px;line-height:1.45}}h1{{margin-bottom:4px}}.muted{{color:#617069}}.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:24px 0}}.card{{border:1px solid #ccd6d1;border-radius:10px;padding:14px}}.card b{{font-size:20px;display:block}}section{{margin:28px 0}}table{{width:100%;border-collapse:collapse}}td,th{{border-bottom:1px solid #ddd;padding:8px;text-align:left}}.warn{{padding:12px;border:1px solid #b38b25;background:#fff9e6}}@media print{{button{{display:none}}}}</style></head><body>
<button onclick="window.print()">Print / Save PDF</button><p class="muted">KAIZEN AI V{esc(VERSION)} · build {esc(BUILD_ID)} · source {esc(snap['source_mode'])}</p>
<h1>Manufacturing Decision Intelligence Report</h1><p>{esc(snap['incident']['line_name'])} · Run {esc(run_id)}</p>
<div class="grid"><div class="card">Post defect<b>{100*float(k['post_defect_rate']):.2f}%</b><span>Δ {defect_delta:+.2f} pp</span></div><div class="card">Good throughput<b>{float(k['post_good_throughput_uph']):.1f}/h</b></div><div class="card">COPQ / 1k<b>${float(k['copq_per_1000_usd']):,.0f}</b></div><div class="card">L5<b>{esc(val['l5'])}</b></div></div>
<section><h2>Incident</h2><p>{esc(snap['incident']['symptom'])}</p><p>Activation boundary: unit {esc(snap['incident']['activation_unit'])} of {esc(snap['incident']['units'])}.</p></section>
<section><h2>Diagnosis</h2><table><tr><th>Leading hypothesis</th><td>{esc(d['title'])}</td></tr><tr><th>Target</th><td>{esc(d['target'])}</td></tr><tr><th>Evidence score</th><td>{esc(d['evidence_score'])}/100 (ranking index, not probability)</td></tr><tr><th>Status / ambiguity</th><td>{esc(d['status'])} / {esc(d['ambiguity'])}</td></tr></table></section>
<section><h2>Decision</h2><table><tr><th>Recommended intervention</th><td>{esc(dec['recommended_intervention'])}</td></tr><tr><th>Optimizer</th><td>{esc(dec['optimizer_method'])}</td></tr><tr><th>MILP / exact oracle agreement</th><td>{esc(dec['milp_oracle_agreement'])}</td></tr><tr><th>First-year net value</th><td>{value}</td></tr></table></section>
<section><h2>Validation / uncertainty</h2><p>Uncertainty verdict: <b>{esc(val['uncertainty_verdict'])}</b>. Best next measurement: <b>{esc(val['best_next_measurement'])}</b>.</p><div class="warn">{esc(snap['causal_policy'])}</div></section>
<section><h2>Reproducibility</h2><p>This report is generated from deterministic KAIZEN engineering engines for the selected run. Gemini is not used to calculate report metrics. Export the canonical CSV and JSON snapshot from Mission Control for audit/replay.</p></section>
</body></html>'''


@app.get("/api/runs/{run_id}/report", response_class=HTMLResponse)
def engineering_report(run_id: str) -> HTMLResponse:
    try:
        registry.get(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return HTMLResponse(_report_html(run_id))


@app.get("/api/runs/{run_id}/quality/overview")
def quality_overview(run_id: str) -> dict[str, Any]:
    """Return validated DEFINE/MEASURE analytics using observable records only."""
    try:
        stored = registry.get(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    result = stored.result
    return {
        "run_id": run_id,
        "version": VERSION,
        "build_id": BUILD_ID,
        "quality": build_quality_overview(
            result.records,
            result.activation_unit,
            line_name=result.config.line_name,
            seed=result.config.seed,
        ),
        "truth_revealed": stored.revealed,
    }


@app.get("/api/runs/{run_id}/ie/overview")
def ie_overview(run_id: str) -> dict[str, Any]:
    """Return V0.3 Industrial Engineering analytics using observable records only."""
    try:
        stored = registry.get(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    result = stored.result
    return {
        "run_id": run_id,
        "version": VERSION,
        "build_id": BUILD_ID,
        "ie": build_ie_overview(result.records, result.activation_unit),
        "truth_revealed": stored.revealed,
    }


@app.get("/api/runs/{run_id}/investigation/overview")
def investigation_overview(run_id: str) -> dict[str, Any]:
    """Return V0.4 ranked observational hypotheses using observable records only."""
    try:
        stored = registry.get(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    result = stored.result
    return {
        "run_id": run_id,
        "version": VERSION,
        "build_id": BUILD_ID,
        "investigation": build_investigation_overview(result.records, result.activation_unit),
        "truth_revealed": stored.revealed,
    }


@app.get("/api/runs/{run_id}/arena/overview")
def arena_overview(run_id: str) -> dict[str, Any]:
    """Return the V0.5 blind investigation timeline and frozen prediction snapshot."""
    try:
        stored = registry.get(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    result = stored.result
    return {
        "run_id": run_id,
        "version": VERSION,
        "build_id": BUILD_ID,
        "arena": build_arena_overview(result.records, result.activation_unit),
        "truth_revealed": stored.revealed,
    }


@app.get("/api/runs/{run_id}/simulation/overview")
def simulation_overview(run_id: str) -> dict[str, Any]:
    """Return V0.6 paired counterfactual simulations using observable records only."""
    try:
        stored = registry.get(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    result = stored.result
    return {
        "run_id": run_id,
        "version": VERSION,
        "build_id": BUILD_ID,
        "simulation": build_simulation_overview(result.records, result.activation_unit),
        "truth_revealed": stored.revealed,
    }


@app.post("/api/runs/{run_id}/simulation/what-if")
def simulation_what_if(run_id: str, payload: WhatIfRequest) -> dict[str, Any]:
    """Run one paired what-if replay. Ground truth/scenario code is not provided to the simulation engine."""
    try:
        stored = registry.get(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if payload.intervention_code not in INTERVENTION_CATALOG:
        raise HTTPException(status_code=422, detail="Unknown intervention code")
    result = stored.result
    try:
        what_if = run_what_if(
            result.records, result.activation_unit, payload.intervention_code,
            effectiveness=payload.effectiveness, demand_multiplier=payload.demand_multiplier,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "run_id": run_id,
        "version": VERSION,
        "build_id": BUILD_ID,
        "what_if": what_if,
        "truth_revealed": stored.revealed,
    }


@app.get("/api/runs/{run_id}/optimizer/overview")
def optimizer_overview(run_id: str) -> dict[str, Any]:
    """Return V0.7 exact binary portfolio optimization under default plant-manager constraints."""
    try:
        stored = registry.get(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    result = stored.result
    return {
        "run_id": run_id,
        "version": VERSION,
        "build_id": BUILD_ID,
        "optimizer": build_optimizer_overview(result.records, result.activation_unit),
        "truth_revealed": stored.revealed,
    }


@app.post("/api/runs/{run_id}/optimizer/solve")
def optimizer_solve(run_id: str, payload: OptimizerRequest) -> dict[str, Any]:
    """Solve the intervention portfolio exactly over the six binary candidate actions."""
    try:
        stored = registry.get(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    result = stored.result
    try:
        solution = solve_improvement_portfolio(
            result.records, result.activation_unit,
            budget_usd=payload.budget_usd,
            max_downtime_hours=payload.max_downtime_hours,
            min_good_throughput_uph=payload.min_good_throughput_uph,
            max_defect_rate=payload.max_defect_rate,
            annual_volume_units=payload.annual_volume_units,
            effectiveness=payload.effectiveness,
            demand_multiplier=payload.demand_multiplier,
            min_evidence_score=payload.min_evidence_score,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "run_id": run_id,
        "version": VERSION,
        "build_id": BUILD_ID,
        "optimizer": solution,
        "truth_revealed": stored.revealed,
    }


@app.get("/api/runs/{run_id}/cape/plan")
def cape_plan(run_id: str, budget_usd: float = 900.0, max_downtime_hours: float = 2.5, max_experiment_runs: int = 4) -> dict[str, Any]:
    """Allocate a governed portfolio of next experiments using the CAPE-Loop MILP."""
    try:
        stored = registry.get(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    result = stored.result
    try:
        cape = allocate_experiment_portfolio(
            result.records, result.activation_unit,
            budget_usd=budget_usd,
            max_downtime_hours=max_downtime_hours,
            max_experiment_runs=max_experiment_runs,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "run_id": run_id, "version": VERSION, "build_id": BUILD_ID,
        "cape": cape, "truth_revealed": stored.revealed,
    }


@app.get("/api/runs/{run_id}/cape/certificate")
def cape_certificate(run_id: str, budget_usd: float = 900.0, max_downtime_hours: float = 2.5, max_experiment_runs: int = 4) -> dict[str, Any]:
    """Bind the CAPE allocation, observable evidence and causal firewall into a review certificate."""
    try:
        stored = registry.get(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    result = stored.result
    try:
        cape = allocate_experiment_portfolio(
            result.records, result.activation_unit, budget_usd=budget_usd,
            max_downtime_hours=max_downtime_hours, max_experiment_runs=max_experiment_runs,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    cert = certify_cape_plan(
        run_id=run_id, records=result.records, cape=cape, source_mode=result.source_mode,
        truth_revealed=stored.revealed, version=VERSION, build_id=BUILD_ID,
    )
    return {"certificate": cert, "verification": verify_cape_certificate(cert)}


@app.get("/api/runs/{run_id}/control/plan")
def control_plan(run_id: str) -> dict[str, Any]:
    """Return a deterministic DMAIC CONTROL plan without fabricating realized benefit."""
    try:
        stored = registry.get(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    result = stored.result
    return {
        "run_id": run_id, "version": VERSION, "build_id": BUILD_ID,
        "control": build_control_plan(result.records, result.activation_unit, line_name=result.config.line_name, seed=result.config.seed),
        "source_mode": result.source_mode, "truth_revealed": stored.revealed,
    }


@app.get("/api/runs/{run_id}/active/overview")
def active_overview(run_id: str) -> dict[str, Any]:
    """Return V0.9 uncertainty, value-of-information and next-investigation guidance from observable data only."""
    try:
        stored = registry.get(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    result = stored.result
    active = build_active_investigation_overview(result.records, result.activation_unit)
    if run_id in active_probe_results:
        active["last_probe_result"] = active_probe_results[run_id]
    if run_id in experiment_results:
        active["experiment_result"] = experiment_results[run_id]
        active["causal_confirmation"] = {
            "level_5": "UNLOCKED" if experiment_results[run_id]["causal_confirmation"]["passed"] else "LOCKED",
            **experiment_results[run_id]["causal_confirmation"],
        }
    return {
        "run_id": run_id, "version": VERSION, "build_id": BUILD_ID,
        "active": active, "truth_revealed": stored.revealed,
    }


@app.post("/api/runs/{run_id}/active/probe")
def active_probe(run_id: str, payload: ProbeRequest) -> dict[str, Any]:
    """Execute one additional observational discrimination probe. Never unlocks causal confirmation."""
    try:
        stored = registry.get(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    result = stored.result
    try:
        probe = execute_observational_probe(result.records, result.activation_unit, payload.probe_code)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    active_probe_results[run_id] = probe
    return {
        "run_id": run_id, "version": VERSION, "build_id": BUILD_ID,
        "probe": probe, "truth_revealed": stored.revealed,
    }


@app.get("/api/runs/{run_id}/experiment/design")
def experiment_design(run_id: str) -> dict[str, Any]:
    """Generate a predeclared controlled experiment from the blind observational diagnosis."""
    try:
        stored = registry.get(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    result = stored.result
    return {
        "run_id": run_id, "version": VERSION, "build_id": BUILD_ID,
        "design": build_experiment_design(result.records, result.activation_unit),
        "truth_revealed": stored.revealed,
    }


@app.post("/api/runs/{run_id}/experiment/execute")
def experiment_execute(run_id: str, payload: ExperimentExecuteRequest) -> dict[str, Any]:
    """Execute an authorized controlled synthetic DOE. Hidden truth shapes the synthetic physical response but is never returned."""
    try:
        stored = registry.get(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not payload.authorized:
        raise HTTPException(status_code=403, detail="Controlled DOE execution requires explicit authorization.")
    result = stored.result
    if result.source_mode != "DEMO":
        raise HTTPException(status_code=409, detail="Synthetic DOE execution is available only in DEMO mode. For real/external data, execute the approved experiment physically and ingest the resulting observations.")
    try:
        experiment = execute_controlled_experiment(
            result.records, result.activation_unit, result.scenario_code,
            payload.experiment_code, seed=result.config.seed,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    experiment_results[run_id] = experiment
    return {
        "run_id": run_id, "version": VERSION, "build_id": BUILD_ID,
        "experiment": experiment,
        "truth_revealed": stored.revealed,
        "ground_truth_returned": False,
    }


@app.get("/api/runs/{run_id}/human-vs-ai")
def human_vs_ai_status(run_id: str) -> dict[str, Any]:
    try:
        stored = registry.get(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    result = stored.result
    inv = build_investigation_overview(result.records, result.activation_unit)
    human = human_predictions.get(run_id)
    ai = build_arena_overview(result.records, result.activation_unit)["prediction_snapshot"]
    out = {
        "available_choices": [
            {"code": h["code"], "title": h["title"], "target": h["target"], "evidence_score": h["evidence_score"]}
            for h in inv["ranked_hypotheses"]
        ],
        "human_prediction": human,
        "ai_prediction": ai,
        "truth_revealed": stored.revealed,
    }
    if stored.revealed and human:
        out["human_score"] = score_human_prediction(human, result.scenario_code)
        out["ai_score"] = score_revealed_diagnosis(result.records, result.activation_unit, result.scenario_code, result.ground_truth)
    return {"run_id": run_id, "version": VERSION, "build_id": BUILD_ID, "human_vs_ai": out}


@app.post("/api/runs/{run_id}/human-vs-ai/predict")
def human_vs_ai_predict(run_id: str, payload: HumanPredictionRequest) -> dict[str, Any]:
    try:
        stored = registry.get(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if stored.revealed:
        raise HTTPException(status_code=409, detail="Human prediction must be frozen before ground truth is revealed.")
    if run_id in human_predictions:
        raise HTTPException(status_code=409, detail="Human prediction is already frozen for this run.")
    result = stored.result
    try:
        frozen = freeze_human_prediction(result.records, result.activation_unit, payload.hypothesis_code)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    human_predictions[run_id] = frozen
    return {"run_id": run_id, "version": VERSION, "build_id": BUILD_ID, "human_prediction": frozen}


@app.get("/api/ai/status")
def gemini_status() -> dict[str, Any]:
    return {"version": VERSION, "build_id": BUILD_ID, "ai": ai_status()}


@app.post("/api/runs/{run_id}/ai/ask")
def ai_ask(run_id: str, payload: AIAskRequest) -> dict[str, Any]:
    """Ask Gemini to reason over KAIZEN engineering tools. Ground truth is never provided to the AI layer."""
    try:
        stored = registry.get(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    result = stored.result
    status = ai_status()
    try:
        answer = ask_kaizen(
            result.records, result.activation_unit, payload.question, mode=payload.mode,
            seed=result.config.seed, line_name=result.config.line_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        # V0.8.2 hardens the live Gemini boundary: unexpected SDK/tool exceptions must never
        # collapse into an opaque local HTTP 500. Do not include secrets in this message.
        raise HTTPException(
            status_code=502,
            detail=f"Gemini integration failure ({type(exc).__name__}): {str(exc)}",
        ) from exc
    return {
        "run_id": run_id, "version": VERSION, "build_id": BUILD_ID,
        "ai": answer.model_dump(), "truth_revealed": stored.revealed,
    }


@app.post("/api/runs/{run_id}/arena/reveal-score")
def arena_reveal_score(run_id: str) -> dict[str, Any]:
    """Explicitly reveal sealed truth and score the blind diagnosis against it."""
    try:
        stored = registry.get(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    result = stored.result
    if result.source_mode != "DEMO":
        raise HTTPException(status_code=409, detail="External data has no sealed synthetic ground truth to reveal or score.")
    # Freeze/compute the diagnosis before changing reveal state. The investigator itself
    # still receives only observable records and activation boundary.
    score = score_revealed_diagnosis(
        result.records, result.activation_unit, result.scenario_code, result.ground_truth
    )
    truth = registry.reveal(run_id)
    return {
        "run_id": run_id,
        "version": VERSION,
        "build_id": BUILD_ID,
        "ground_truth": truth,
        "scorecard": score,
        "warning": "Ground truth is now explicitly revealed for post-hoc diagnosis scoring.",
    }


@app.post("/api/runs/{run_id}/reveal")
def reveal_ground_truth(run_id: str) -> dict[str, Any]:
    try:
        stored = registry.get(run_id)
        if stored.result.source_mode != "DEMO":
            raise HTTPException(status_code=409, detail="External data has no sealed synthetic ground truth.")
        truth = registry.reveal(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"run_id": run_id, "ground_truth": truth, "warning": "Ground truth is now explicitly revealed."}


@app.get("/api/runs/{run_id}/ground-truth", include_in_schema=False)
def ground_truth_status(run_id: str) -> dict[str, Any]:
    """Non-discoverable helper used by the demo UI after the reveal action."""
    try:
        stored = registry.get(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if stored.result.source_mode != "DEMO":
        raise HTTPException(status_code=409, detail="External data has no sealed synthetic ground truth.")
    if not stored.revealed:
        raise HTTPException(status_code=403, detail="Ground truth is sealed. Use the explicit reveal action.")
    return {"run_id": run_id, "ground_truth": stored.result.ground_truth}
