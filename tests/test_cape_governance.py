from copy import deepcopy
from kaizen_factory.models import FactoryConfig
from kaizen_factory.simulator import simulate_factory
from kaizen_cape import allocate_experiment_portfolio, certify_cape_plan, verify_cape_certificate


def test_cape_assurance_binds_observable_data_resources_and_firewall():
    run=simulate_factory(FactoryConfig(seed=55,units=420,activation_fraction=.42),'gage_measurement_drift',reveal_truth=True)
    cape=allocate_experiment_portfolio(run.records,run.activation_unit,budget_usd=700,max_downtime_hours=2,max_experiment_runs=4)
    cert=certify_cape_plan(run_id=run.run_id,records=run.records,cape=cape,source_mode=run.source_mode,truth_revealed=False,version='1.0.0',build_id='test')
    assert cert['decision_state']=='EXPERIMENT_PORTFOLIO_REVIEW'
    assert cert['production_process_change_allowed'] is False
    assert cert['causal_firewall']['causal_confirmation_unlocked'] is False
    assert verify_cape_certificate(cert)['valid'] is True
    bad=deepcopy(cert); bad['resource_use']['budget_usd'] += 1
    assert verify_cape_certificate(bad)['valid'] is False
