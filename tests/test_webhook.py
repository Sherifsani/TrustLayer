"""
Webhook endpoint tests.
Requires demo users to be seeded first: python db/seed.py
"""
import hashlib
import hmac
import json
import os

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

load_dotenv()

from api.main import app
from api.models.db_models import SquadEvent, User
from db.session import SessionLocal

client = TestClient(app)

ADAEZE_EMAIL = "adaeze@trustlayer.demo"

VALID_PAYLOAD = {
    "Event": "charge_successful",
    "TransactionRef": "SQTEST_PYTEST_WEBHOOK_001",
    "Body": {
        "amount": 100000,
        "transaction_ref": "SQTEST_PYTEST_WEBHOOK_001",
        "transaction_status": "Success",
        "email": ADAEZE_EMAIL,
        "transaction_type": "Card",
        "merchant_amount": 100000,
        "created_at": "2025-08-24T15:26:38.994",
    },
}


def _sign(body_bytes: bytes) -> str:
    secret = os.getenv("SQUAD_SECRET_KEY", "")
    return hmac.new(secret.encode(), body_bytes, hashlib.sha512).hexdigest()


def test_valid_webhook_stores_event():
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.email == ADAEZE_EMAIL).first()
        assert user is not None, "Adaeze must be seeded before running tests"
        count_before = db.query(SquadEvent).filter(SquadEvent.user_id == user.id).count()
    finally:
        db.close()

    body_bytes = json.dumps(VALID_PAYLOAD, separators=(",", ":")).encode()
    sig = _sign(body_bytes)

    resp = client.post(
        "/webhook/squad",
        content=body_bytes,
        headers={"Content-Type": "application/json", "x-squad-encrypted-body": sig},
    )
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

    db = SessionLocal()
    try:
        count_after = db.query(SquadEvent).filter(SquadEvent.user_id == user.id).count()
        assert count_after == count_before + 1, "Webhook must create a SquadEvent record"
    finally:
        db.close()


def test_invalid_signature_returns_200():
    body_bytes = json.dumps(VALID_PAYLOAD).encode()
    resp = client.post(
        "/webhook/squad",
        content=body_bytes,
        headers={
            "Content-Type": "application/json",
            "x-squad-encrypted-body": "this_is_not_a_valid_signature",
        },
    )
    # Squad must never receive a non-200 — even on bad signatures
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_non_charge_event_returns_200():
    body_bytes = json.dumps({"Event": "transfer_initiated"}).encode()
    resp = client.post(
        "/webhook/squad",
        content=body_bytes,
        headers={
            "Content-Type": "application/json",
            "x-squad-encrypted-body": "irrelevant",
        },
    )
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
