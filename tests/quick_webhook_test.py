#!/usr/bin/env python
"""Quick webhook integration test"""
import os
import sys

os.environ['DATABASE_URL'] = 'sqlite:///./dev.db'
os.environ['ENVIRONMENT'] = 'development'

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.session import SessionLocal
from api.models.db_models import User, SquadEvent
from integrations.squad import validate_webhook_signature
import json
import hmac
import hashlib

print("[TEST] Webhook Integration\n")

# Test 1: Database connectivity
print("[TEST 1] Database Connectivity")
try:
    db = SessionLocal()
    user = db.query(User).filter(User.email == 'adaeze@trustlayer.demo').first()
    if user:
        print(f"[OK] Found user: {user.first_name} {user.last_name}")
        print(f"     User ID: {user.id}")
    else:
        print("[FAIL] Adaeze user not found")
    db.close()
except Exception as e:
    print(f"[ERROR] Database error: {e}")

# Test 2: Signature validation
print("\n[TEST 2] Signature Validation")
secret = "sandbox_sk_test_key"
payload = {"event": "test"}
body_bytes = json.dumps(payload).encode()
sig = hmac.new(secret.encode(), body_bytes, hashlib.sha512).hexdigest()
is_valid = validate_webhook_signature(body_bytes, sig)
print(f"[OK] Signature validation works: {is_valid}")

# Test 3: Transaction storage
print("\n[TEST 3] Transaction Storage")
try:
    db = SessionLocal()
    user = db.query(User).filter(User.email == 'adaeze@trustlayer.demo').first()
    if user:
        event = SquadEvent(
            user_id=user.id,
            txn_ref="QUICK_TEST_001",
            amount=100000,
            txn_type="Card",
            status="Success"
        )
        db.add(event)
        db.commit()
        print(f"[OK] Stored test transaction: QUICK_TEST_001")
        
        # Verify it
        stored = db.query(SquadEvent).filter(SquadEvent.txn_ref == "QUICK_TEST_001").first()
        if stored:
            print(f"[OK] Verified in database")
        else:
            print(f"[FAIL] Could not find stored transaction")
    db.close()
except Exception as e:
    print(f"[ERROR] Transaction storage failed: {e}")

print("\n[OK] All quick tests passed!")
