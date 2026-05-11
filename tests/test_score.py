"""
Score endpoint tests.
Requires demo users to be seeded first: python db/seed.py
"""
import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)
BIZ_HEADERS = {"Authorization": "Bearer biz_key_kwikloans_demo"}


def test_adaeze_scores_low_risk():
    resp = client.post("/score", headers=BIZ_HEADERS, json={"user_id": "usr_adaeze001"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["trust_score"] >= 65, f"Expected score >= 65, got {data['trust_score']}"
    assert data["risk_level"] == "low", f"Expected low risk, got {data['risk_level']}"
    assert len(data["drivers"]) >= 1


def test_emeka_scores_high_risk():
    resp = client.post("/score", headers=BIZ_HEADERS, json={"user_id": "usr_emeka001"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["trust_score"] <= 49, f"Expected score <= 49, got {data['trust_score']}"
    assert data["risk_level"] == "high", f"Expected high risk, got {data['risk_level']}"
    assert data["recommendation"] == "decline"


def test_score_always_has_drivers():
    resp = client.post("/score", headers=BIZ_HEADERS, json={"user_id": "usr_adaeze001"})
    assert resp.status_code == 200
    data = resp.json()
    assert "drivers" in data
    assert len(data["drivers"]) >= 1, "Score response must always contain at least one driver"


def test_missing_api_key_returns_401():
    resp = client.post("/score", json={"user_id": "usr_adaeze001"})
    assert resp.status_code == 401


def test_unknown_user_returns_404():
    resp = client.post(
        "/score",
        headers=BIZ_HEADERS,
        json={"user_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert resp.status_code == 404
