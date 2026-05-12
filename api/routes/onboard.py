import asyncio
import hashlib

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.models.db_models import User
from api.models.schemas import OnboardRequest, OnboardResponse
from db.session import get_db
from integrations import dojah

router = APIRouter()


@router.post("/onboard", response_model=OnboardResponse)
async def onboard(payload: OnboardRequest, db: Session = Depends(get_db)):
    (bvn_result, nin_result, liveness_result, phone_result, aml_result) = await asyncio.gather(
        dojah.verify_bvn(payload.bvn, payload.first_name, payload.last_name),
        dojah.lookup_nin(payload.nin),
        dojah.liveness_check(payload.selfie_base64, payload.bvn),
        dojah.check_phone(payload.phone),
        dojah.screen_aml(payload.first_name, payload.last_name, dob=None),
    )

    # Extract individual KYC signal values — degrade gracefully to neutral if any call failed
    bvn_confidence = (
        bvn_result.get("entity", {}).get("bvn", {}).get("confidence_value", 50) / 100
        if "error" not in bvn_result else 0.5
    )

    nin_entity = nin_result.get("entity", {}) if "error" not in nin_result else {}
    nin_watchlisted = 1 if str(nin_entity.get("watch_listed", "NO")).upper() == "YES" else 0

    liveness_score = (
        liveness_result.get("entity", {}).get("confidence_value", 50) / 100
        if "error" not in liveness_result else 0.5
    )

    doc_authentic = 1  # no document uploaded at onboard yet — default to authentic

    phone_entity = phone_result.get("entity", {}) if "error" not in phone_result else {}
    phone_first = str(phone_entity.get("first_name", "")).upper()
    provided_first = str(payload.first_name).upper()
    phone_name_match = 1 if phone_first and phone_first in provided_first else 0

    aml_entity = aml_result.get("entity", {}) if (
        "error" not in aml_result and isinstance(aml_result.get("entity"), dict)
    ) else {}
    aml_risk_raw = str(aml_entity.get("risk_level", "low")).lower()
    aml_risk_level = {"low": 0, "medium": 1, "high": 2}.get(aml_risk_raw, 0)

    kyc_signals = {
        "bvn_confidence": bvn_confidence,
        "nin_watchlisted": nin_watchlisted,
        "liveness_score": liveness_score,
        "doc_authentic": doc_authentic,
        "phone_name_match": phone_name_match,
        "aml_risk_level": aml_risk_level,
    }

    # Weighted identity confidence: BVN 35%, Liveness 35%, NIN 20%, Phone 10%
    identity_confidence = (
        bvn_confidence * 0.35
        + liveness_score * 0.35
        + (1 - nin_watchlisted) * 0.20
        + phone_name_match * 0.10
    )

    # KYC status determination (hard-block overrides confidence threshold)
    flags: list[str] = []
    if nin_watchlisted:
        flags.append("NIN flagged on watchlist")
    if aml_risk_level >= 2:
        flags.append("AML watchlist hit")
    if not bvn_result.get("match") and "error" not in bvn_result:
        flags.append("BVN name mismatch")
    if liveness_score < 0.5:
        flags.append("Liveness check failed")

    if nin_watchlisted or aml_risk_level >= 2:
        kyc_status = "blocked"
    elif identity_confidence >= 0.7:
        kyc_status = "verified"
    else:
        kyc_status = "failed"

    # SHA-256 hash before any DB write — never store raw BVN/NIN
    bvn_hash = hashlib.sha256(payload.bvn.encode()).hexdigest()
    nin_hash = hashlib.sha256(payload.nin.encode()).hexdigest()

    # Prevent duplicate users: if a user with the same BVN/NIN/email exists, update and return that record
    existing = (
        db.query(User)
        .filter(
            (User.bvn_hash == bvn_hash) | (User.nin_hash == nin_hash) | (User.email == str(payload.email))
        )
        .first()
    )

    if existing:
        # Update KYC fields where appropriate and return existing user_id
        existing.kyc_status = kyc_status
        existing.identity_confidence = identity_confidence
        existing.kyc_signals = kyc_signals
        existing.phone = payload.phone
        existing.first_name = payload.first_name
        existing.last_name = payload.last_name
        db.commit()
        db.refresh(existing)
        return OnboardResponse(
            user_id=str(existing.id),
            kyc_status=kyc_status,
            identity_confidence=round(identity_confidence, 4),
            flags=flags,
        )

    user = User(
        bvn_hash=bvn_hash,
        nin_hash=nin_hash,
        phone=payload.phone,
        email=str(payload.email),
        kyc_status=kyc_status,
        identity_confidence=identity_confidence,
        kyc_signals=kyc_signals,
        first_name=payload.first_name,
        last_name=payload.last_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return OnboardResponse(
        user_id=str(user.id),
        kyc_status=kyc_status,
        identity_confidence=round(identity_confidence, 4),
        flags=flags,
    )
