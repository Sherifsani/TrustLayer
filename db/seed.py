"""
Seed the two demo test users exactly as specified in CLAUDE.md.
Run once before the demo: python db/seed.py
Safe to re-run — backfills new fields on existing users.
"""
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv()

from db.session import SessionLocal
from api.models.db_models import User, SquadEvent, TrustScore, Report, Consent

# ── helpers ────────────────────────────────────────────────────────────────

def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()

def _days_ago(n: int) -> datetime:
    return datetime.utcnow() - timedelta(days=n)

def _date(y: int, m: int, d: int) -> datetime:
    return datetime(y, m, d)


# ── Adaeze Okafor ── usr_adaeze001 ─────────────────────────────────────────

def seed_adaeze(db) -> None:
    adaeze = db.query(User).filter(User.user_handle == "usr_adaeze001").first()

    if not adaeze:
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
            first_name="Adaeze",
            last_name="Okonkwo",
            location="Surulere, Lagos",
            created_at=_days_ago(95),
        )
        db.add(adaeze)
        db.flush()

        # 23 successful transactions spread across the last 90 days
        txn_types = ["Card", "Transfer", "Bank"]
        amounts_naira = [
            5000, 8000, 12000, 3000, 15000, 7500, 4200, 9800, 11000, 6300,
            2500, 14000, 8800, 5500, 10000, 3800, 7200, 13000, 4600, 9200,
            6700, 11500, 2800,
        ]
        for i, amount_naira in enumerate(amounts_naira):
            days_back = int(90 * (i + 1) / 24)
            db.add(SquadEvent(
                user_id=adaeze.id,
                txn_ref=f"SQSEED_ADAEZE_{i+1:03d}",
                amount=amount_naira * 100,
                txn_type=txn_types[i % len(txn_types)],
                status="Success",
                created_at=_days_ago(days_back),
            ))

        db.add(SquadEvent(
            user_id=adaeze.id,
            txn_ref="SQSEED_ADAEZE_FAIL_001",
            amount=5000 * 100,
            txn_type="Card",
            status="Failed",
            created_at=_days_ago(45),
        ))

        db.commit()
        print("  ✓ Adaeze Okafor (usr_adaeze001) created — 24 events")
    else:
        # Backfill any new columns added since first seed
        changed = False
        if not adaeze.first_name:
            adaeze.first_name = "Adaeze"
            adaeze.last_name = "Okonkwo"
            adaeze.location = "Surulere, Lagos"
            changed = True
        if changed:
            db.commit()
            print("  ✓ Adaeze — backfilled first_name/last_name/location")
        else:
            print("  Adaeze already seeded — skipping user creation.")

    # Seed score history (wipe and re-seed so we always have 6 clean historical points)
    _seed_adaeze_scores(db, adaeze)

    # Seed reports
    _seed_adaeze_reports(db, adaeze)

    # Seed consents
    _seed_adaeze_consents(db, adaeze)


def _seed_adaeze_scores(db, user) -> None:
    historical_count = db.query(TrustScore).filter(
        TrustScore.user_id == user.id,
        TrustScore.score < 75,
    ).count()
    if historical_count >= 5:
        print("  Adaeze score history already seeded — skipping.")
        return

    # Clear all existing scores and replace with canonical 6-point history
    db.query(TrustScore).filter(TrustScore.user_id == user.id).delete()
    history = [
        (58, _days_ago(240)),
        (62, _days_ago(210)),
        (66, _days_ago(180)),
        (70, _days_ago(120)),
        (74, _days_ago(60)),
        (78, _days_ago(1)),
    ]
    for score_val, ts in history:
        db.add(TrustScore(
            user_id=user.id,
            score=score_val,
            risk_level="low",
            drivers=[
                "Transactions in last 90 days → +12 pts",
                "No dispute history → +8 pts",
                "Strong liveness score → +7 pts",
            ],
            signals_used=["squad_history", "telco_data", "kyc"],
            computed_at=ts,
        ))
    db.commit()
    print("  ✓ Adaeze — 6 historical score points seeded (58 → 78 over 8 months)")


def _seed_adaeze_reports(db, user) -> None:
    if db.query(Report).filter(Report.user_id == user.id).count() >= 3:
        print("  Adaeze reports already seeded — skipping.")
        return

    db.query(Report).filter(Report.user_id == user.id).delete()
    for r in [
        Report(
            user_id=user.id,
            title="Verified Trust Report — May 2026",
            report_type="verified_trust_report",
            recipient_id="sterling_mfb",
            recipient_name="Sterling MFB",
            pages=6,
            status="ready",
            created_at=_date(2026, 5, 8),
        ),
        Report(
            user_id=user.id,
            title="Identity & Income Snapshot",
            report_type="identity_snapshot",
            recipient_id="andela_talent",
            recipient_name="Andela Talent",
            pages=4,
            status="ready",
            created_at=_date(2026, 4, 22),
        ),
        Report(
            user_id=user.id,
            title="Verified Trust Report — Renmoney",
            report_type="verified_trust_report",
            recipient_id="renmoney",
            recipient_name="Renmoney",
            pages=6,
            status="pending",
            created_at=_date(2026, 5, 10),
        ),
    ]:
        db.add(r)
    db.commit()
    print("  ✓ Adaeze — 3 report records seeded")


def _seed_adaeze_consents(db, user) -> None:
    if db.query(Consent).filter(Consent.user_id == user.id).count() >= 3:
        print("  Adaeze consents already seeded — skipping.")
        return

    db.query(Consent).filter(Consent.user_id == user.id).delete()
    
    consents = [
        Consent(
            user_id=user.id,
            business_id="sterling_microfinance",
            granted_signals=["trust_score", "squad_history", "identity_vault"],
            denied_signals=[],
            granted_at=_date(2026, 4, 8),
            expires_at=_date(2026, 5, 8),
            revoked=False,
        ),
        Consent(
            user_id=user.id,
            business_id="renmoney",
            granted_signals=["trust_score", "telco_data"],
            denied_signals=["squad_history", "identity_vault"],
            granted_at=_date(2026, 4, 22),
            expires_at=None,
            revoked=False,
        ),
        Consent(
            user_id=user.id,
            business_id="andela_talent",
            granted_signals=["trust_score", "identity_vault"],
            denied_signals=["telco_data", "squad_history"],
            granted_at=_date(2026, 3, 30),
            expires_at=_date(2026, 6, 30),
            revoked=False,
        ),
    ]
    for c in consents:
        db.add(c)
    db.commit()
    print("  ✓ Adaeze — 3 consent records seeded")


# ── Emeka Eze ── usr_emeka001 ───────────────────────────────────────────────

def seed_emeka(db) -> None:
    emeka = db.query(User).filter(User.user_handle == "usr_emeka001").first()

    if not emeka:
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
            first_name="Emeka",
            last_name="Eze",
            location="Ikeja, Lagos",
            created_at=_days_ago(10),
        )
        db.add(emeka)
        db.flush()

        spike_events = [
            ("Card", 1000000, "Success", 6),
            ("Card",  500000, "Failed",  5),
            ("Card", 1000000, "Success", 4),
            ("Card",  500000, "Failed",  3),
            ("Card", 1000000, "Success", 2),
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
    else:
        changed = False
        if not emeka.first_name:
            emeka.first_name = "Emeka"
            emeka.last_name = "Eze"
            emeka.location = "Ikeja, Lagos"
            changed = True
        if changed:
            db.commit()
            print("  ✓ Emeka — backfilled first_name/last_name/location")
        else:
            print("  Emeka already seeded — skipping.")


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
