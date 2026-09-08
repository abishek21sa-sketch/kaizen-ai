from fastapi.testclient import TestClient

from app.main import app, registry

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["version"] == "1.0.0"
    assert body["build_id"] == "20260815-v100-public1"
    assert body["ai"]["provider"] == "Google Gemini"
    assert body["ai"]["function_calling"] is True
    assert "no-store" in r.headers.get("cache-control", "")


def test_create_blind_run_does_not_expose_root_cause_or_scenario_code():
    r = client.post("/api/runs", json={"seed": 9001, "units": 500, "scenario": "fixture_wear_temp"})
    assert r.status_code == 201
    body = r.json()
    serialized = str(body).lower()
    assert "progressive wear" not in serialized
    assert "fixture_wear_temp" not in serialized

    listing = client.get("/api/runs").json()
    serialized_listing = str(listing).lower()
    assert "scenario_code" not in serialized_listing
    assert "progressive wear" not in serialized_listing


def test_records_endpoint_exposes_only_observable_data():
    created = client.post("/api/runs", json={"seed": 101, "units": 300, "scenario": "gage_measurement_drift"}).json()
    run_id = created["run_id"]
    r = client.get(f"/api/runs/{run_id}/records?limit=20")
    assert r.status_code == 200
    keys = set(r.json()["records"][0])
    assert "torque_actual_nm" not in keys
    assert "true_defect" not in keys
    assert "measurement_bias_nm" not in keys


def test_ground_truth_requires_explicit_reveal():
    created = client.post("/api/runs", json={"seed": 202, "units": 300, "scenario": "tool_calibration_drift"}).json()
    run_id = created["run_id"]
    blocked = client.get(f"/api/runs/{run_id}/ground-truth")
    assert blocked.status_code == 403

    reveal = client.post(f"/api/runs/{run_id}/reveal")
    assert reveal.status_code == 200
    truth = reveal.json()["ground_truth"]
    assert "Calibration bias developing" in truth["scenario"]["root_cause"]

    allowed = client.get(f"/api/runs/{run_id}/ground-truth")
    assert allowed.status_code == 200


def test_unknown_run_is_404():
    assert client.get("/api/runs/KZN-NOTREAL/summary").status_code == 404


def test_unknown_scenario_is_rejected():
    r = client.post("/api/runs", json={"seed": 1, "units": 200, "scenario": "made_up"})
    assert r.status_code == 422


def test_root_serves_kaizen_ui():
    r = client.get("/")
    assert r.status_code == 200
    assert "KAIZEN AI" in r.text
    assert "V1.0.0" in r.text
    assert "20260815-v100-public1" in r.text
    assert "__KAIZEN_VERSION__" not in r.text
    assert "__KAIZEN_BUILD_ID__" not in r.text


def test_invalid_small_run_is_rejected_with_structured_validation():
    r = client.post("/api/runs", json={"seed": 43, "units": 50, "scenario": "random"})
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert isinstance(detail, list)
    assert any("greater than or equal to 100" in item.get("msg", "") for item in detail)


def test_frontend_resets_truth_and_formats_validation_errors():
    from pathlib import Path
    js = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text(encoding="utf-8")
    assert "function resetTruthForNewRun()" in js
    assert "$('revealBtn').textContent = 'REVEAL + SCORE';" in js
    assert "function formatApiError(detail, status)" in js
    assert "Units must be a whole number between 100 and 250,000." in js


def test_quality_overview_uses_observable_records_and_is_available_before_reveal():
    created = client.post("/api/runs", json={"seed": 42, "units": 600, "scenario": "gage_measurement_drift"}).json()
    run_id = created["run_id"]
    r = client.get(f"/api/runs/{run_id}/quality/overview")
    assert r.status_code == 200
    body = r.json()
    assert body["truth_revealed"] is False
    assert body["quality"]["data_quality"]["status"] == "PASS"
    assert body["quality"]["evidence_state"]["ground_truth_dependency"] is False
    serialized = str(body).lower()
    assert "torque_actual_nm" not in serialized
    assert "measurement_bias_nm" not in serialized
    assert "latent_fault_strength" not in serialized


def test_v02_frontend_exposes_quality_sections():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    html = (root / "static" / "index.html").read_text(encoding="utf-8")
    js = (root / "static" / "app.js").read_text(encoding="utf-8")
    assert "Lean Six Sigma" in html
    assert "PROCESS CAPABILITY" in html
    assert "Gage R&amp;R" in html
    assert "loadQuality" in js
    assert "/quality/overview" in js


def test_ie_overview_is_available_before_reveal_and_has_no_truth_dependency():
    created = client.post("/api/runs", json={"seed": 42, "units": 800, "scenario": "changeover_deterioration"}).json()
    run_id = created["run_id"]
    r = client.get(f"/api/runs/{run_id}/ie/overview")
    assert r.status_code == 200
    body = r.json()
    assert body["truth_revealed"] is False
    assert body["ie"]["evidence_state"]["ground_truth_dependency"] is False
    assert body["ie"]["takt"]["takt_seconds_per_unit"] == 45.0
    serialized = str(body).lower()
    assert "latent_fault_strength" not in serialized
    assert "root_cause" not in serialized


def test_ie_metrics_do_not_change_after_ground_truth_reveal():
    created = client.post("/api/runs", json={"seed": 314, "units": 700, "scenario": "calibration_microstops"}).json()
    run_id = created["run_id"]
    before = client.get(f"/api/runs/{run_id}/ie/overview").json()["ie"]
    assert client.post(f"/api/runs/{run_id}/reveal").status_code == 200
    after = client.get(f"/api/runs/{run_id}/ie/overview").json()["ie"]
    assert before == after


def test_v03_frontend_exposes_industrial_engineering_sections():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    html = (root / "static" / "index.html").read_text(encoding="utf-8")
    js = (root / "static" / "app.js").read_text(encoding="utf-8")
    assert "INDUSTRIAL ENGINEERING" in html
    assert "Little's Law" in html
    assert "loadIE" in js
    assert "/ie/overview" in js


def test_investigation_overview_is_available_before_reveal_and_has_no_truth_dependency():
    created = client.post("/api/runs", json={"seed": 42, "units": 700, "scenario": "tool_calibration_drift"}).json()
    run_id = created["run_id"]
    r = client.get(f"/api/runs/{run_id}/investigation/overview")
    assert r.status_code == 200
    body = r.json()
    assert body["truth_revealed"] is False
    inv = body["investigation"]
    assert inv["top_suspect"]["code"] == "MACHINE_TORQUE_BIAS"
    assert inv["top_suspect"]["causal_status"] == "NOT_CONFIRMED"
    serialized = str(body).lower()
    assert "latent_fault_strength" not in serialized
    assert "torque_actual_nm" not in serialized
    assert "true_defect" not in serialized
    assert "tool_calibration_drift" not in serialized


def test_investigation_does_not_change_after_ground_truth_reveal():
    created = client.post("/api/runs", json={"seed": 81, "units": 700, "scenario": "supplier_resin_shift"}).json()
    run_id = created["run_id"]
    before = client.get(f"/api/runs/{run_id}/investigation/overview").json()["investigation"]
    assert client.post(f"/api/runs/{run_id}/reveal").status_code == 200
    after = client.get(f"/api/runs/{run_id}/investigation/overview").json()["investigation"]
    assert before == after


def test_v04_frontend_exposes_statistical_investigator_sections():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    html = (root / "static" / "index.html").read_text(encoding="utf-8")
    js = (root / "static" / "app.js").read_text(encoding="utf-8")
    assert "STATISTICAL INVESTIGATOR" in html
    assert "CORRELATION ≠ CAUSE GATE" in html
    assert "EVIDENCE LEDGER" in html
    assert "ADJUSTED REGRESSION" in html
    assert "FACTORIAL ANOVA" in html
    assert "loadInvestigation" in js
    assert "/investigation/overview" in js


def test_v042_frontend_backend_build_sync_guard_is_present():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    html = (root / "static" / "index.html").read_text(encoding="utf-8")
    js = (root / "static" / "app.js").read_text(encoding="utf-8")
    assert "KAIZEN_EXPECTED_VERSION" in html
    assert "KAIZEN_EXPECTED_BUILD" in html
    assert "BUILD MISMATCH" in js
    assert "buildCompatible" in js
    assert "h.build_id !== expectedBuild" in js


def test_seed42_api_attribution_is_m2_before_reveal():
    created = client.post("/api/runs", json={"seed": 42, "units": 2500, "scenario": "tool_calibration_drift"}).json()
    run_id = created["run_id"]
    inv = client.get(f"/api/runs/{run_id}/investigation/overview").json()["investigation"]
    assert inv["top_suspect"]["target"] == "M2"
    assert inv["top_suspect"]["attribution"]["direction"] == "INCREASE"
    blocked = client.get(f"/api/runs/{run_id}/ground-truth")
    assert blocked.status_code == 403
