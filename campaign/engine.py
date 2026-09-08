from collections import Counter
import statistics
from tenx.engine import _run_decision_core
from empirical.backbone import run_empirical_reference
SEEDS=[5,9,17,27,35,47,61]
def run_campaign():
    runs=[_run_decision_core(s) for s in SEEDS]; choices=[r['decision']['next_probe'] for r in runs]; c=Counter(choices); modal,n=c.most_common(1)[0]; regrets=[]
    for r in runs:
        vals=r['predictions']; sel=r['decision']['next_probe']; naive=r['counterfactual']['choice']; regrets.append(float(vals[sel]-vals[naive]))
    emp=run_empirical_reference(); delta=float(emp.get('domain_diagnostics',{}).get('metrics',{}).get('defect_delta_pp',0)); meanreg=statistics.mean(regrets); stability=n/len(runs)
    state='CONTROLLED_EXPERIMENT_REVIEW' if meanreg>0 and stability>=.7 else 'CONTINUE_DIAGNOSIS'
    return {'campaign':'Closed-Loop Improvement Campaign','campaign_identity':'evidence regret + causal-resource frontier','scenario_count':len(runs),'scenario_seeds':SEEDS,'state':state,'modal_probe':modal,'modal_share':round(stability,4),'mean_evidence_regret':round(meanreg,5),'incident_defect_delta_pp':delta,'scenario_matrix':[{'seed':s,'probe':r['decision']['next_probe'],'score':r['decision']['score'],'naive_probe':r['counterfactual']['choice'],'evidence_regret':round(regrets[i],5),'bandit_mae':r['model_validation']['value']} for i,(s,r) in enumerate(zip(SEEDS,runs))],'ai_synthesis':{'why':f'{modal} is selected in {n}/{len(runs)} investigations and avoids {meanreg:.3f} mean learned-value regret versus the cheap probe.','challenge':'Observational replay and bandit value can prioritize evidence; neither grants causal authority.','recommended_operator_action':'Run the discriminating diagnostic, then authorize a controlled experiment only through the causal gate.','abstention_conditions':['no reliable probe','evidence ambiguity remains high','measurement system untrusted','causal firewall locked']},'action_queue':['run discriminating probe','update competing-hypothesis evidence','design governed controlled experiment','allocate CAPE resources','review sustainment/rollback plan'],'human_authority':'CONTINUOUS_IMPROVEMENT_ENGINEER','causal_authority':'NONE','autonomous_execution':False,'empirical_provenance':{'mode':emp.get('data_mode'),'promotion':emp.get('empirical_promotion')}}
