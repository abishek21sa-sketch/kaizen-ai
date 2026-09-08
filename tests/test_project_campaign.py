from campaign.engine import run_campaign

def test_project_decision_campaign():
    out=run_campaign()
    assert out["scenario_count"] >= 7
    assert out["campaign"] == 'Closed-Loop Improvement Campaign'
    assert out["campaign_identity"] == 'evidence regret + causal-resource frontier'
    assert 'mean_evidence_regret' in out
    assert len(out["scenario_matrix"]) == out["scenario_count"]
    assert len(out["action_queue"]) >= 4
    assert out["human_authority"]
    assert out["autonomous_execution"] is False
    assert out["ai_synthesis"]["recommended_operator_action"]
