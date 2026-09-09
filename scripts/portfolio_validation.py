from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from kaizen_factory.models import FactoryConfig
from kaizen_factory.simulator import simulate_factory
from kaizen_cape import allocate_experiment_portfolio, allocate_rank_greedy_baseline
from kaizen_optimizer import solve_improvement_portfolio

run=simulate_factory(FactoryConfig(seed=2026,units=700,activation_fraction=.42),'gage_measurement_drift',reveal_truth=True)
cape=allocate_experiment_portfolio(run.records,run.activation_unit,budget_usd=900,max_downtime_hours=2.5,max_experiment_runs=4)
greedy=allocate_rank_greedy_baseline(run.records,run.activation_unit,budget_usd=900,max_downtime_hours=2.5,max_experiment_runs=4)
opt=solve_improvement_portfolio(run.records,run.activation_unit,budget_usd=25000,max_downtime_hours=8,min_good_throughput_uph=70,max_defect_rate=1.0)
payload={
'release':'KAIZEN_AI_PORTFOLIO_RELEASE',
'cape':cape,
'cape_ablation':{'rank_greedy':greedy,'information_priority_gain_vs_greedy':cape['objective_information_priority']-greedy['objective_information_priority']},
'intervention_optimizer':{'status':opt['solver']['status'],'best_portfolio':opt.get('best_portfolio'),'milp_oracle_agreement':opt['solver'].get('agreement_with_exact_oracle')},
'governance':{'causal_confirmation_unlocked':False,'production_write_allowed':False,'human_authorization_required':True},
'evidence_boundary':'Synthetic Hidden Factory benchmark; no real-factory causal or financial-performance claim.'}
(ROOT/'docs'/'PORTFOLIO_VALIDATION.json').write_text(json.dumps(payload,indent=2,sort_keys=True))
if cape['status']!='OPTIMAL' or cape['objective_information_priority'] + 1e-9 < greedy['objective_information_priority']: raise SystemExit('CAPE validation failed')
print(json.dumps({'release':payload['release'],'cape_status':cape['status'],'cape_resources':cape['resource_use'],'cape_gain_vs_greedy':payload['cape_ablation']['information_priority_gain_vs_greedy'],'optimizer_status':payload['intervention_optimizer']['status'],'governance':payload['governance']},indent=2))
print('KAIZEN_PORTFOLIO_VALIDATION=PASS')
