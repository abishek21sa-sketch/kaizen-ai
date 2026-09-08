from pathlib import Path
import csv,statistics,collections,math
ROOT=Path(__file__).resolve().parents[1]
def _rate(rr):return sum(str(r['observed_defect']).lower() in {'true','1'} for r in rr)/max(1,len(rr))
def domain_diagnostics():
 rows=list(csv.DictReader((ROOT/'examples/external_replay_seed42.csv').open())); half=len(rows)//2; pre,post=rows[:half],rows[half:]
 bygage=collections.defaultdict(list); bymachine=collections.defaultdict(list)
 for r in rows:bygage[r['gage_id']].append(r);bymachine[r['machine_id']].append(r)
 g={k:round(_rate(v),4) for k,v in bygage.items()}; m={k:round(_rate(v),4) for k,v in bymachine.items()}
 def terr(rr):return [abs(float(r['torque_measured_nm'])-float(r['torque_target_nm'])) for r in rr]
 return {'analysis':'factory incident evidence stratification','metrics':{'records':len(rows),'pre_defect_rate':round(_rate(pre),4),'post_defect_rate':round(_rate(post),4),'defect_delta_pp':round(100*(_rate(post)-_rate(pre)),3),'pre_mean_abs_torque_error':round(statistics.fmean(terr(pre)),4),'post_mean_abs_torque_error':round(statistics.fmean(terr(post)),4)},'defect_rate_by_gage':g,'defect_rate_by_machine':m,'highest_risk_gage':max(g,key=g.get),'highest_risk_machine':max(m,key=m.get),'decision_signal':'TRACE-LIFT should prioritize the discriminating probe for the strongest post-event equipment/measurement signal before CAPE allocates controlled experiments.','evidence_boundary':'Replay evidence is controlled repository evidence and is not external production validation.'}
