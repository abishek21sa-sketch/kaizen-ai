from __future__ import annotations
from tenx.engine import run_decision
from campaign.engine import run_campaign
from empirical.backbone import run_empirical_reference

def lifecycle_report():
    d=run_decision(29); v=d['model_validation']; preds=d.get('predictions',{})
    vals=[float(x) for x in preds.values()] if isinstance(preds,dict) else []
    spread=(max(vals)-min(vals)) if vals else 0.0; mae=float(v.get('value',0) or 0)
    state='REPLAY_REQUIRED' if mae>.35 else ('EXPLORATION_WATCH' if spread<.18 else 'ACTIVE')
    public_data=d.get('public_data_backbone',{})
    return {'public_data_state':public_data.get('dataset_state'),'public_evidence_gate':d.get('public_evidence_gate'),'model_family':d['ml_family'],'target':d['prediction_target'],'validation':v,'arm_value_spread':round(spread,5),'learning_state':state,'retrain_trigger':'offline replay + confidence reset if information-value MAE >0.35 or arm-value spread collapses','monitoring':['context coverage','arm-selection balance','offline replay regret','information reward drift','causal-gate status'],'registry_state':'BANDIT_ACTIVE' if state=='ACTIVE' else 'BANDIT_CHALLENGER','source_mode':run_empirical_reference().get('data_mode')}

def run_agent():
    d=run_decision(29); life=lifecycle_report(); c=run_campaign(); steps=['assemble competing hypotheses','score evidence ambiguity','update LinUCB probe values']
    state='INVESTIGATE'
    public_gate=d.get('public_evidence_gate')
    if public_gate=='REFERENCE_MODE_HOLD_FOR_REAL_DATA_CLAIM':
        steps.append('flag external public-data acquisition gap; prohibit real-data performance claim')
        state='REFERENCE_MODE_HOLD'
    if life['learning_state']=='REPLAY_REQUIRED': steps += ['replay historical investigations','reset exploration confidence','do not allocate intervention budget']; state='LEARNING_HOLD'
    else: steps += ['invoke TRACE-LIFT probe triage','collect selected diagnostic evidence','open controlled experiment gate','allocate experiment portfolio with CAPE-Loop']
    return {'agent':'Continuous Improvement Investigator','objective':'reduce evidence regret before spending intervention budget','prediction':d.get('predictions'),'decision':d['decision'],'decision_state':state,'chosen_tool_sequence':steps,'why_this_sequence':'bandit confidence determines which ambiguity-reducing probe is worth running before CAPE resource allocation','challenge':d['counterfactual'],'ml_lifecycle':life,'experiment_portfolio_state':c.get('state'),'operator_actions':['run selected diagnostic','review hypothesis separation','authorize DOE only after causal gate','approve CAPE resource allocation'],'human_authority':d['human_authority'],'autonomous_execution':False,'causal_authority':'NONE'}
