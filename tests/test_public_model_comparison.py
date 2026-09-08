from empirical.public_data_backbone import data_backbone_status


def test_hydraulic_case_exposes_condition_model_comparison():
    case = data_backbone_status()["case_study"]
    names = {row["model"] for row in case["model_comparison"]}
    assert {"majority_condition_baseline", "nearest_centroid_challenger"} <= names
    assert case["selected_model"] in names
