from fastapi.testclient import TestClient

from app.main import app


def test_public_backbone_endpoint_exposes_claim_boundary_and_case_study():
    response = TestClient(app).get("/api/data/public-backbone")
    assert response.status_code == 200
    body = response.json()
    assert body["dataset"]
    assert body["claim_boundary"]
    assert body["autonomous_execution"] is False
    assert body["case_study"]["status"] in {"ACTIVE", "ACQUISITION_REQUIRED", "TARGET_UNAVAILABLE"}
