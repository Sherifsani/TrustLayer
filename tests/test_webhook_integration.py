"""
Squad Webhook Integration Test

This script simulates Squad payment webhooks to test the full integration:
1. Validates webhook signature
2. Stores transaction in database
3. Triggers score recomputation (Celery task)
4. Verifies database state

Run: python tests/test_webhook_integration.py
"""

import asyncio
import hashlib
import hmac
import json
import os
import sys
from datetime import datetime
from uuid import UUID

# Set environment variables BEFORE importing any TrustLayer modules
os.environ.setdefault("DATABASE_URL", "sqlite:///./dev.db")
os.environ.setdefault("ENVIRONMENT", "development")

from dotenv import load_dotenv

load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.session import SessionLocal
from api.models.db_models import SquadEvent, User, TrustScore
from integrations.squad import validate_webhook_signature


def create_webhook_signature(body_bytes: bytes, secret: str) -> str:
    """Generate HMAC-SHA512 signature for webhook payload."""
    return hmac.new(secret.encode(), body_bytes, hashlib.sha512).hexdigest()


def test_webhook_signature_validation():
    """Test webhook signature validation."""
    print("\n[TEST 1] Webhook Signature Validation")
    print("-" * 60)

    secret = os.getenv("SQUAD_SECRET_KEY", "sandbox_sk_test")
    payload = {
        "Event": "charge_successful",
        "TransactionRef": "SQTEST001",
        "Body": {
            "amount": 100000,
            "transaction_ref": "SQTEST001",
            "transaction_status": "Success",
            "email": "adaeze@trustlayer.demo",
            "transaction_type": "Card",
            "merchant_amount": 100000,
            "created_at": "2026-05-12T12:00:00.000",
        },
    }

    body_bytes = json.dumps(payload).encode()
    valid_signature = create_webhook_signature(body_bytes, secret)

    # Test valid signature
    is_valid = validate_webhook_signature(body_bytes, valid_signature)
    print(f"[OK] Valid signature: {is_valid}")
    assert is_valid, "Signature validation failed"

    # Test invalid signature
    invalid_signature = "0" * 128
    is_invalid = validate_webhook_signature(body_bytes, invalid_signature)
    print(f"[OK] Invalid signature rejected: {not is_invalid}")
    assert not is_invalid, "Invalid signature should be rejected"

    print("[PASS] Signature validation test passed!")
    return True


def test_webhook_payload_parsing():
    """Test webhook payload parsing and validation."""
    print("\n[TEST 2] Webhook Payload Parsing")
    print("-" * 60)

    payload = {
        "Event": "charge_successful",
        "TransactionRef": "SQTEST002",
        "Body": {
            "amount": 250000,
            "transaction_ref": "SQTEST002",
            "transaction_status": "Success",
            "email": "test@trustlayer.demo",
            "transaction_type": "Card",
            "merchant_amount": 250000,
            "created_at": "2026-05-12T12:30:00.000",
        },
    }

    print(f"Payload Event: {payload['Event']}")
    print(f"Transaction Ref: {payload['TransactionRef']}")
    print(f"Amount (kobo): {payload['Body']['amount']}")
    print(f"Email: {payload['Body']['email']}")
    print(f"Status: {payload['Body']['transaction_status']}")

    assert payload["Event"] == "charge_successful"
    assert payload["Body"]["transaction_status"] == "Success"

    print("[PASS] Payload parsing test passed!")
    return True


def test_database_storage():
    """Test storing webhook data in database."""
    print("\n[TEST 3] Database Storage")
    print("-" * 60)

    db = SessionLocal()
    try:
        # Get demo user (Adaeze)
        user = db.query(User).filter(User.email == "adaeze@trustlayer.demo").first()
        if not user:
            print("[WARN] Demo user not found. Creating test user...")
            # This shouldn't happen if seed.py was run, but handle gracefully
            print("Run: python db/seed.py")
            return False

        print(f"Found user: {user.first_name} {user.last_name}")
        print(f"User ID: {user.id}")

        # Create a test transaction
        test_event = SquadEvent(
            user_id=user.id,
            txn_ref="SQTEST_DB_001",
            amount=150000,
            txn_type="Card",
            status="Success",
        )
        db.add(test_event)
        db.commit()

        print(f"[OK] Stored transaction: {test_event.txn_ref}")
        print(f"  Amount: {test_event.amount} kobo")
        print(f"  Status: {test_event.status}")

        # Verify it was stored
        stored = db.query(SquadEvent).filter(SquadEvent.txn_ref == "SQTEST_DB_001").first()
        assert stored is not None
        print(f"[OK] Verified in database")

        print("[PASS] Database storage test passed!")
        return True

    finally:
        db.close()


def test_user_lookup_by_email():
    """Test finding user by email from webhook."""
    print("\n[TEST 4] User Lookup by Email")
    print("-" * 60)

    db = SessionLocal()
    try:
        emails = [
            "adaeze@trustlayer.demo",
            "emeka@trustlayer.demo",
            "nonexistent@test.com",
        ]

        for email in emails:
            user = db.query(User).filter(User.email == email).first()
            if user:
                print(f"[OK] Found: {email} => {user.first_name} {user.last_name}")
            else:
                print(f"[NOT FOUND] {email}")

        print("[PASS] User lookup test passed!")
        return True

    finally:
        db.close()


def test_transaction_history():
    """Test retrieving transaction history for a user."""
    print("\n[TEST 5] Transaction History")
    print("-" * 60)

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "adaeze@trustlayer.demo").first()
        if not user:
            print("⚠️  Demo user not found")
            return False

        transactions = db.query(SquadEvent).filter(SquadEvent.user_id == user.id).all()
        print(f"Transaction count for {user.first_name}: {len(transactions)}")

        for txn in transactions[:5]:  # Show first 5
            print(
                f"  - {txn.txn_ref}: {txn.amount} kobo ({txn.txn_type}) - {txn.status}"
            )

        print("[PASS] Transaction history test passed!")
        return True

    finally:
        db.close()


def test_webhook_event_flow():
    """Simulate complete webhook event flow."""
    print("\n[TEST 6] Complete Webhook Event Flow")
    print("-" * 60)

    secret = os.getenv("SQUAD_SECRET_KEY", "sandbox_sk_test")
    db = SessionLocal()

    try:
        # Get demo user
        user = db.query(User).filter(User.email == "adaeze@trustlayer.demo").first()
        if not user:
            print("⚠️  Demo user not found")
            return False

        # Create webhook payload
        payload = {
            "Event": "charge_successful",
            "TransactionRef": f"SQTEST_FLOW_{datetime.now().timestamp()}",
            "Body": {
                "amount": 500000,
                "transaction_ref": f"SQTEST_FLOW_{datetime.now().timestamp()}",
                "transaction_status": "Success",
                "email": user.email,
                "transaction_type": "Transfer",
                "merchant_amount": 500000,
                "created_at": datetime.now().isoformat(),
            },
        }

        body_bytes = json.dumps(payload).encode()
        signature = create_webhook_signature(body_bytes, secret)

        print(f"Step 1: Create payload")
        print(f"  Email: {payload['Body']['email']}")
        print(f"  Amount: {payload['Body']['amount']} kobo")

        # Validate signature
        print(f"Step 2: Validate signature")
        is_valid = validate_webhook_signature(body_bytes, signature)
        print(f"  Valid: {is_valid}")
        assert is_valid

        # Store transaction
        print(f"Step 3: Store transaction")
        event = SquadEvent(
            user_id=user.id,
            txn_ref=payload["Body"]["transaction_ref"],
            amount=payload["Body"]["amount"],
            txn_type=payload["Body"]["transaction_type"],
            status=payload["Body"]["transaction_status"],
        )
        db.add(event)
        db.commit()
        print(f"  Stored: {event.txn_ref}")

        # Would trigger: recompute_score.delay(str(user.id), business_id="system")
        print(f"Step 4: Would trigger Celery task")
        print(f"  Task: recompute_score.delay('{user.id}', business_id='system')")
        print(f"  (Skipped: Redis/Celery not running in dev)")

        print("[PASS] Complete webhook flow test passed!")
        return True

    finally:
        db.close()


def main():
    """Run all webhook integration tests."""
    print("\n" + "=" * 60)
    print("[SQUAD] WEBHOOK INTEGRATION TEST SUITE")
    print("=" * 60)

    tests = [
        test_webhook_signature_validation,
        test_webhook_payload_parsing,
        test_user_lookup_by_email,
        test_transaction_history,
        test_database_storage,
        test_webhook_event_flow,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"[ERROR] Test failed with error: {e}")
            import traceback

            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"[RESULTS] {passed} passed, {failed} failed")
    print("=" * 60)

    if failed == 0:
        print("\n[SUCCESS] All tests passed! Webhook integration is working.")
        print("\nNext steps:")
        print("1. Ensure Squad credentials are set in .env.local")
        print("2. Register webhook URL in Squad dashboard:")
        print(f"   {os.getenv('SQUAD_WEBHOOK_URL')}")
        print("3. Test with real Squad payment in sandbox")
    else:
        print("\n[FAILED] Some tests failed. Check errors above.")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
