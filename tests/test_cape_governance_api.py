from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)

def test_cape_certificate_endpoint_is_verified_and_human_gated():
    created=client.post('/api/runs',json={'seed':144,'units':360,'scenario':'gage_measurement_drift'})
    assert created.status_code==201
    run_id=created.json()['run_id']
    r=client.get(f'/api/runs/{run_id}/cape/certificate?budget_usd=700&max_downtime_hours=2&max_experiment_runs=4')
    assert r.status_code==200
    assert r.headers['X-Request-ID'].startswith('kzn-')
    assert float(r.headers['X-Response-Time-Ms']) >= 0
    b=r.json()
    assert b['verification']['valid'] is True
    assert b['certificate']['production_process_change_allowed'] is False
    assert b['certificate']['decision_state']=='EXPERIMENT_PORTFOLIO_REVIEW'
