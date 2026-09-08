from kaizen_factory.models import FactoryConfig
from kaizen_factory.simulator import simulate_factory
from kaizen_cape import allocate_experiment_portfolio


def _records():
    r = simulate_factory(FactoryConfig(seed=17, units=400, activation_fraction=0.42), "gage_measurement_drift", reveal_truth=True)
    return r.records, r.activation_unit


def test_cape_respects_shared_resources_and_never_unlocks_causality():
    records, activation = _records()
    out = allocate_experiment_portfolio(records, activation, budget_usd=500, max_downtime_hours=1.5, max_experiment_runs=3)
    assert out["status"] == "OPTIMAL"
    assert out["resource_use"]["budget_usd"] <= 500 + 1e-9
    assert out["resource_use"]["downtime_hours"] <= 1.5 + 1e-9
    assert out["resource_use"]["runs"] <= 3
    assert out["causal_firewall"]["causal_confirmation_unlocked"] is False


def test_cape_diminishing_returns_can_diversify_experiment_portfolio():
    records, activation = _records()
    out = allocate_experiment_portfolio(records, activation, budget_usd=1000, max_downtime_hours=3.0, max_experiment_runs=5, max_replicates_per_hypothesis=2)
    assert out["status"] == "OPTIMAL"
    assert sum(x["replicates"] for x in out["allocation"]) <= 5
    assert len({x["hypothesis_code"] for x in out["allocation"]}) == len(out["allocation"])


def test_cape_joint_allocation_beats_or_matches_rank_greedy_reference():
    from kaizen_factory.models import FactoryConfig
    from kaizen_factory.simulator import simulate_factory
    from kaizen_cape import allocate_experiment_portfolio, allocate_rank_greedy_baseline
    run=simulate_factory(FactoryConfig(seed=2026,units=700,activation_fraction=.42),'gage_measurement_drift',reveal_truth=True)
    kwargs=dict(budget_usd=900,max_downtime_hours=2.5,max_experiment_runs=4)
    cape=allocate_experiment_portfolio(run.records,run.activation_unit,**kwargs)
    greedy=allocate_rank_greedy_baseline(run.records,run.activation_unit,**kwargs)
    assert cape['status']=='OPTIMAL'
    assert cape['objective_information_priority'] >= greedy['objective_information_priority'] - 1e-9
    assert cape['causal_firewall']['causal_confirmation_unlocked'] is False
    assert greedy['causal_confirmation_unlocked'] is False
