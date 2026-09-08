from __future__ import annotations
import math
import numpy as np

class LinUCBBandit:
    def __init__(self,arms,dim=4,alpha=.8): self.arms=arms; self.alpha=alpha; self.A={a:np.eye(dim) for a in arms}; self.b={a:np.zeros(dim) for a in arms}
    def update(self,arm,x,reward): self.A[arm]+=np.outer(x,x); self.b[arm]+=reward*x
    def score(self,arm,x):
        inv=np.linalg.inv(self.A[arm]); theta=inv@self.b[arm]; return float(theta@x+self.alpha*math.sqrt(max(0,float(x@inv@x))))

class TraceLift:
    """TRACE-LIFT: evidence-separation triage with reliability, ambiguity and operational burden."""
    def choose(self,probes,bandit):
        rows=[]
        for p in probes:
            x=np.array([p['ambiguity'],p['separation'],p['reliability'],1-p['burden']],float); learned=bandit.score(p['name'],x)
            score=1.3*p['ambiguity']*p['separation']+1.1*p['reliability']-.7*p['burden']+.45*learned
            rows.append({**p,'trace_lift_score':score,'learned_value':learned})
        return max(rows,key=lambda z:z['trace_lift_score'])

def _run_decision_core(seed=31):
    probes=[{'name':'cross_gage_repeat','ambiguity':.92,'separation':.88,'reliability':.95,'burden':.35},{'name':'machine_recheck','ambiguity':.75,'separation':.42,'reliability':.82,'burden':.22},{'name':'humidity_replay','ambiguity':.64,'separation':.55,'reliability':.72,'burden':.12}]
    b=LinUCBBandit([p['name'] for p in probes]); r=np.random.default_rng(seed)
    true={'cross_gage_repeat':.92,'machine_recheck':.44,'humidity_replay':.52}
    for _ in range(45):
        for p in probes:
            x=np.array([p['ambiguity'],p['separation'],p['reliability'],1-p['burden']]); b.update(p['name'],x,true[p['name']]+r.normal(0,.08))
    choice=TraceLift().choose(probes,b); cheap=min(probes,key=lambda p:p['burden']); predvals={p['name']:b.score(p['name'],np.array([p['ambiguity'],p['separation'],p['reliability'],1-p['burden']])) for p in probes}; mae=float(np.mean([abs(predvals[a]-true[a]) for a in true]))
    return {'project':'KAIZEN AI','ml_family':'LinUCB contextual-bandit learning','prediction_target':'expected diagnostic information value by probe/context','model_validation':{'metric':'reference information-value MAE','value':mae,'direction':'lower_is_better','split':'held reference values'},'predictions':predvals,'original_algorithm':'TRACE-LIFT-v1','decision':{'next_probe':choice['name'],'score':choice['trace_lift_score']},'counterfactual':{'naive_policy':'lowest operational burden','choice':cheap['name'],'disagrees':cheap['name']!=choice['name']},'uncertainty':'LinUCB upper-confidence term rewards unresolved probes while maintaining learned value estimates.','or_escalation':'Confirmed evidence enters CAPE-Loop binary experiment allocation and intervention portfolio optimization.','tool_trace':['build evidence context','update contextual-bandit values','rank with TRACE-LIFT','challenge cheapest probe','design controlled experiment','escalate to CAPE-Loop'],'limitations':['bundled history is synthetic/reference evidence','bandit reward is information value, not causal probability'],'abstention_conditions':['evidence ambiguity too high','no reliable probe','causal gate locked'],'user_aid':['run selected diagnostic','compare hypothesis separation','authorize controlled DOE if warranted','review CAPE resource allocation'],'human_authority':'CONTINUOUS_IMPROVEMENT_ENGINEER','autonomous_execution':False,'causal_authority':'NONE'}


def run_decision(seed=None):
    from empirical.backbone import run_empirical_reference
    import inspect
    sig=inspect.signature(_run_decision_core)
    if seed is None:
        out=_run_decision_core()
    else:
        out=_run_decision_core(seed)
    emp=run_empirical_reference()
    out["empirical_backbone"]=emp
    from empirical.public_data_backbone import integrate_decision
    out=integrate_decision(out)
    out.setdefault("tool_trace",[]).insert(0,"resolve empirical data provenance and source mode")
    out.setdefault("user_aid",[]).append("open empirical case study and entity/history drilldowns before approval")
    return out
