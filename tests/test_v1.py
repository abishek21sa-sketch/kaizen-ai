from __future__ import annotations

import csv
import io
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from kaizen_data import contract_document, normalize_records
from kaizen_factory.models import FactoryConfig
from kaizen_factory.simulator import simulate_factory
from kaizen_optimizer import solve_improvement_portfolio

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[1]


def _records(seed: int = 42, units: int = 160):
    result = simulate_factory(FactoryConfig(seed=seed, units=units), "random", reveal_truth=True)
    return result


def test_v1_health_exposes_data_modes_and_milp():
    h = client.get('/health').json()
    assert h['version'] == '1.0.0'
    assert h['build_id'] == '20260815-v100-public1'
    assert h['data_modes'] == ['DEMO', 'FILE', 'REPLAY', 'LIVE']
    assert h['manufacturing_data_contract'] == '1.0'
    assert h['milp_optimizer_enabled'] is True


def test_manufacturing_data_contract_is_explicit_and_non_fabricating():
    c = contract_document()
    assert c['version'] == '1.0'
    assert 'torque_measured_nm' in c['full_engine_required_fields']
    assert 'queue_wait_s' in c['full_engine_required_fields']
    assert 'LIVE' in c['source_modes']
    assert 'cannot use KAIZEN' in c['real_world_causal_policy'] or 'real intervention' in c['real_world_causal_policy']


def test_adapter_derives_only_documented_fields_and_maps_aliases():
    sim = _records(units=120)
    rows = [dict(x) for x in sim.records]
    for row in rows:
        row['equipment_id'] = row.pop('machine_id')
        row['serial_number'] = row.pop('unit_id')
        row.pop('unit_index', None)
        row.pop('total_processing_s', None)
    normalized, report = normalize_records(rows)
    assert len(normalized) == 120
    assert normalized[0]['machine_id'] in {'M1','M2'}
    assert normalized[0]['unit_id'].startswith('ACT-')
    assert report['fabricated_fields'] == []
    assert set(report['derived_fields']) == {'unit_index','total_processing_s'}
    assert report['readiness']['full_engine_ready'] is True


def test_external_json_run_is_analyzable_but_has_no_synthetic_truth_or_doe():
    sim = _records(units=140)
    r = client.post('/api/data/runs', json={
        'records': sim.records,
        'activation_unit': sim.activation_unit,
        'line_name': 'Plant Alpha',
        'source_mode': 'FILE',
        'mapping': {},
    })
    assert r.status_code == 201
    body = r.json()
    assert body['source_mode'] == 'FILE'
    assert body['mapping_report']['readiness']['full_engine_ready'] is True
    run_id = body['run_id']
    assert client.get(f'/api/runs/{run_id}/quality/overview').status_code == 200
    assert client.get(f'/api/runs/{run_id}/ie/overview').status_code == 200
    assert client.get(f'/api/runs/{run_id}/investigation/overview').status_code == 200
    assert client.post(f'/api/runs/{run_id}/arena/reveal-score').status_code == 409
    design = client.get(f'/api/runs/{run_id}/experiment/design').json()['design']
    blocked = client.post(f'/api/runs/{run_id}/experiment/execute', json={'experiment_code': design['experiment_code'], 'authorized': True})
    assert blocked.status_code == 409


def test_csv_replay_import_and_replay_endpoints():
    sim = _records(seed=7, units=120)
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(sim.records[0].keys()))
    writer.writeheader(); writer.writerows(sim.records)
    r = client.post('/api/data/import/csv', data={
        'activation_unit': str(sim.activation_unit),
        'line_name': 'Replay Line',
        'source_mode': 'REPLAY',
        'mapping_json': '{}',
    }, files={'file': ('history.csv', stream.getvalue(), 'text/csv')})
    assert r.status_code == 201
    run_id = r.json()['run_id']
    manifest = client.get(f'/api/runs/{run_id}/replay/manifest').json()
    assert manifest['events'] == 120
    assert manifest['source_mode'] == 'REPLAY'
    events = client.get(f'/api/runs/{run_id}/replay/events?offset=10&limit=5').json()
    assert len(events['events']) == 5
    assert events['events'][0]['unit_index'] == 10


def test_live_session_can_buffer_and_finalize_full_engine_records():
    sim = _records(seed=8, units=120)
    created = client.post('/api/live/sessions', json={'line_name': 'Live Cell', 'activation_unit': sim.activation_unit, 'mapping': {}})
    assert created.status_code == 201
    sid = created.json()['session_id']
    a = client.post(f'/api/live/sessions/{sid}/events', json={'records': sim.records[:60]})
    b = client.post(f'/api/live/sessions/{sid}/events', json={'records': sim.records[60:]})
    assert a.json()['buffered_records'] == 60
    assert b.json()['buffered_records'] == 120
    final = client.post(f'/api/live/sessions/{sid}/finalize', json={})
    assert final.status_code == 201
    assert final.json()['source_mode'] == 'LIVE'
    run_id = final.json()['run_id']
    assert client.get(f'/api/runs/{run_id}/mission-control').status_code == 200


def test_milp_solver_is_real_and_agrees_with_exact_oracle_on_current_catalog():
    sim = _records(seed=42, units=1000)
    o = solve_improvement_portfolio(sim.records, sim.activation_unit)
    assert 'MILP' in o['solver']['method']
    assert o['solver']['milp']['status'] == 'OPTIMAL'
    assert o['solver']['milp']['success'] is True
    assert o['solver']['oracle_agreement'] is True
    assert o['solver']['milp']['selected_intervention_codes'] == o['best_portfolio']['intervention_codes']


def test_mission_control_and_printable_report_are_deterministic_tool_outputs():
    created = client.post('/api/runs', json={'seed':42,'units':600,'scenario':'random','activation_fraction':0.42}).json()
    rid = created['run_id']
    m = client.get(f'/api/runs/{rid}/mission-control')
    assert m.status_code == 200
    data = m.json()
    assert data['source_mode'] == 'DEMO'
    assert 'MILP' in data['decision']['optimizer_method']
    assert data['validation']['l5'] in {'LOCKED','UNLOCKED'}
    report = client.get(f'/api/runs/{rid}/report')
    assert report.status_code == 200
    assert 'Manufacturing Decision Intelligence Report' in report.text
    assert 'Gemini is not used to calculate report metrics' in report.text


def test_ui_is_workspace_based_not_one_endless_default_scroll():
    html = (ROOT/'static'/'index.html').read_text(encoding='utf-8')
    css = (ROOT/'static'/'styles.css').read_text(encoding='utf-8')
    js = (ROOT/'static'/'app.js').read_text(encoding='utf-8')
    for workspace in ['mission','measure','operations','diagnose','decide','validate','data']:
        assert f'data-workspace-target="{workspace}"' in html
    assert 'MISSION CONTROL' in html
    assert 'CAREER FAIR MODE' not in html
    assert '3-MINUTE RECRUITER DEMO' not in html
    assert 'DATA / INTEGRATION' in html
    assert '.workspace-section:not(.active-workspace)' in css
    assert "function setWorkspace(name" in js
    assert "toggleCareerMode" not in js
    assert "career-mode" not in css


def test_control_plan_completes_dmaic_without_fabricating_realized_savings():
    created = client.post('/api/runs', json={'seed':42,'units':600,'scenario':'tool_calibration_drift','activation_fraction':0.42}).json()
    rid = created['run_id']
    r = client.get(f'/api/runs/{rid}/control/plan')
    assert r.status_code == 200
    c = r.json()['control']
    assert c['state'] == 'CONTROL_PLAN_READY'
    assert c['basis']['leading_hypothesis'] == 'MACHINE_TORQUE_BIAS'
    assert c['monitoring']['primary_metric'] == 'torque_error_nm'
    assert c['benefits_verification']['minimum_stabilization_window_units'] == 500
    assert c['handoff']['realized_benefits_verified'] is False
    assert c['handoff']['control_plan_is_causal_proof'] is False
