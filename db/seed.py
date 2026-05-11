"""
Seed the two demo test users exactly as specified in CLAUDE.md.
Run once before the demo: python db/seed.py
Safe to re-run — skips users that already exist.
"""
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv()

from db.session import SessionLocal
from api.models.db_models import User, SquadEvent, TrustScore

# ── helpers ────────────────────────────────────────────────────────────────

def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()

def _days_ago(n: int) -> datetime:
    return datetime.utcnow() - timedelta(days=n)


# ── Adaeze Okafor ── usr_adaeze001 ─────────────────────────────────────────

def seed_adaeze(db) -> None:
    if db.query(User).filter(User.user_handle == "usr_adaeze001").first():
        print("  Adaeze already seeded — skipping.")
        return

    adaeze = User(
        user_handle="usr_adaeze001",
        bvn_hash=_sha256("22222222222"),
        nin_hash=_sha256("70123456789"),
        phone="09011111111",
        email="adaeze@trustlayer.demo",
        kyc_status="verified",
        identity_confidence=0.94,
        kyc_signals={
            "bvn_confidence": 0.97,
            "nin_watchlisted": 0,
            "liveness_score": 0.91,
            "doc_authentic": 1,
            "phone_name_match": 1,
            "aml_risk_level": 0,
        },
        created_at=_days_ago(95),
    )
    db.add(adaeze)
    db.flush()  # get adaeze.id before creating child rows

    # 23 successful transactions spread across the last 90 days
    txn_types = ["Card", "Transfer", "Bank"]
    amounts_naira = [
        5000, 8000, 12000, 3000, 15000, 7500, 4200, 9800, 11000, 6300,
        2500, 14000, 8800, 5500, 10000, 3800, 7200, 13000, 4600, 9200,
        6700, 11500, 2800,
    ]  # 23 values — all in naira; stored as kobo (× 100)

    for i, amount_naira in enumerate(amounts_naira):
        days_back = int(90 * (i + 1) / 24)  # evenly spread over 90 days
        db.add(SquadEvent(
            user_id=adaeze.id,
            txn_ref=f"SQSEED_ADAEZE_{i+1:03d}",
            amount=amount_naira * 100,           # kobo
            txn_type=txn_types[i % len(txn_types)],
            status="Success",
            created_at=_days_ago(days_back),
        ))

    # 1 failed event (failure rate ≈ 0.04)
    db.add(SquadEvent(
        user_id=adaeze.id,
        txn_ref="SQSEED_ADAEZE_FAIL_001",
        amount=5000 * 100,
        txn_type="Card",
        status="Failed",
        created_at=_days_ago(45),
    ))

    # Pre-seeded trust score (used for report display before first live score)
    db.add(TrustScore(
        user_id=adaeze.id,
        score=78,
        risk_level="low",
        drivers=[
            "Transactions in last 90 days → +12 pts",
            "No dispute history → +8 pts",
            "Strong liveness score → +7 pts",
        ],
        signals_used=["squad_history", "telco_data", "kyc"],
        computed_at=_days_ago(1),
    ))

    db.commit()
    print("  ✓ Adaeze Okafor (usr_adaeze001) seeded — 24 events, score 78, risk low")


# ── Emeka Eze ── usr_emeka001 ───────────────────────────────────────────────

def seed_emeka(db) -> None:
    if db.query(User).filter(User.user_handle == "usr_emeka001").first():
        print("  Emeka already seeded — skipping.")
        return

    emeka = User(
        user_handle="usr_emeka001",
        bvn_hash=_sha256("33333333333"),
        nin_hash=_sha256("70987654321"),
        phone="08022222222",
        email="emeka@trustlayer.demo",
        kyc_status="failed",
        identity_confidence=0.41,
        kyc_signals={
            "bvn_confidence": 0.38,
            "nin_watchlisted": 0,
            "liveness_score": 0.42,
            "doc_authentic": 1,
            "phone_name_match": 0,
            "aml_risk_level": 1,
        },
        created_at=_days_ago(10),
    )
    db.add(emeka)
    db.flush()

    # 5 events in the last 7 days — velocity spike pattern
    # Amounts stored in kobo; 500000 kobo = ₦5,000 and 1000000 kobo = ₦10,000
    # (scaled so avg_txn_amount lands in fraud-detectable range after / 100)
    spike_events = [
        ("Card", 1000000, "Success", 6),   # ₦10,000
        ("Card",  500000, "Failed",  5),   # ₦5,000
        ("Card", 1000000, "Success", 4),   # ₦10,000
        ("Card",  500000, "Failed",  3),   # ₦5,000
        ("Card", 1000000, "Success", 2),   # ₦10,000
    ]
    for i, (txn_type, amount, status, days_back) in enumerate(spike_events):
        db.add(SquadEvent(
            user_id=emeka.id,
            txn_ref=f"SQSEED_EMEKA_{i+1:03d}",
            amount=amount,
            txn_type=txn_type,
            status=status,
            created_at=_days_ago(days_back),
        ))

    db.add(TrustScore(
        user_id=emeka.id,
        score=31,
        risk_level="high",
        drivers=[
            "Unusual transaction pattern detected",
            "Low liveness check score → -18 pts",
            "High transaction failure rate → -12 pts",
        ],
        signals_used=["squad_history", "telco_data", "kyc"],
        computed_at=_days_ago(1),
    ))

    db.commit()
    print("  ✓ Emeka Eze (usr_emeka001) seeded — 5 events, score 31, risk high")


# ── main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Seeding demo users …")
    db = SessionLocal()
    try:
        seed_adaeze(db)
        seed_emeka(db)
    finally:
        db.close()
    print("Done.")
