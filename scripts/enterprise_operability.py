from __future__ import annotations
import json,time
from copy import deepcopy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from kaizen_factory.models import FactoryConfig
from kaizen_factory.simulator import simulate_factory
from kaizen_cape import allocate_experiment_portfolio, allocate_rank_greedy_baseline, certify_cape_plan, verify_cape_certificate

start=time.perf_counter()
run=simulate_factory(FactoryConfig(seed=2026,units=700,activation_fraction=.42),'gage_measurement_drift',reveal_truth=True)
kwargs=dict(budget_usd=900,max_downtime_hours=2.5,max_experiment_runs=4)
cape=allocate_experiment_portfolio(run.records,run.activation_unit,**kwargs)
greedy=allocate_rank_greedy_baseline(run.records,run.activation_unit,**kwargs)
cert=certify_cape_plan(run_id=run.run_id,records=run.records,cape=cape,source_mode=run.source_mode,truth_revealed=False,version='1.0.0',build_id='enterprise-operability')
bad=deepcopy(cert); bad['production_process_change_allowed']=True
tamper=verify_cape_certificate(bad)
invalid_rejected=False
try:
    allocate_experiment_portfolio(run.records,run.activation_unit,budget_usd=-1)
except ValueError:
    invalid_rejected=True
elapsed=time.perf_counter()-start
checks={
    'cape_optimal':cape['status']=='OPTIMAL',
    'joint_allocation_not_worse_than_greedy':cape['objective_information_priority'] >= greedy['objective_information_priority']-1e-9,
    'causal_firewall_locked':cape['causal_firewall']['causal_confirmation_unlocked'] is False,
    'certificate_valid':verify_cape_certificate(cert)['valid'] is True,
    'tampering_detected':tamper['valid'] is False,
    'invalid_resource_envelope_rejected':invalid_rejected,
    'reference_runtime_under_30s':elapsed<30,
}
payload={'phase':'ENTERPRISE_OPERABILITY_V1','status':'PASS' if all(checks.values()) else 'HOLD','checks':checks,'runtime_seconds':elapsed,'cape_information_priority':cape.get('objective_information_priority'),'greedy_information_priority':greedy.get('objective_information_priority'),'certificate_sha256':cert['certificate_sha256'],'claim_boundary':'Synthetic/observable manufacturing evidence; CAPE allocates experiments and never authorizes causal or production claims.'}
(ROOT/'artifacts'/'enterprise_operability.json').write_text(json.dumps(payload,indent=2,sort_keys=True,default=str))
print(json.dumps({'status':payload['status'],'checks':checks,'runtime_seconds':round(elapsed,3)},indent=2))
if payload['status']!='PASS': raise SystemExit('KAIZEN_ENTERPRISE_OPERABILITY=HOLD')
print('KAIZEN_ENTERPRISE_OPERABILITY=PASS')
