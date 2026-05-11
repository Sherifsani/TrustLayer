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

    # Extract values — degrade gracefully if any Dojah call failed
    bvn_conf = float(bvn_result.get("confidence", 0.5)) if "error" not in bvn_result else 0.5
    liveness_val = float(liveness_result.get("score", 0.5)) if "error" not in liveness_result else 0.5
    nin_watchlisted = bool(nin_result.get("watchlisted", False)) if "error" not in nin_result else False
    nin_valid = 0.0 if nin_watchlisted else 1.0
    raw_phone_match = phone_result.get("name_match", 0.5) if "error" not in phone_result else 0.5
    phone_match = (1.0 if raw_phone_match else 0.0) if isinstance(raw_phone_match, bool) else float(raw_phone_match)

    # Weighted identity confidence: BVN 35%, Liveness 35%, NIN 20%, Phone 10%
    identity_confidence = (
        bvn_conf * 0.35
        + liveness_val * 0.35
        + nin_valid * 0.20
        + phone_match * 0.10
    )

    # AML risk level — Dojah returns int 0/1/2 or string
    aml_level = aml_result.get("risk_level", 0) if "error" not in aml_result else 0
    try:
        aml_high = int(aml_level) >= 2
    except (TypeError, ValueError):
        aml_high = str(aml_level).lower() in ("high", "2")

    # KYC status determination (hard-block overrides confidence threshold)
    flags: list[str] = []
    if nin_watchlisted:
        flags.append("NIN flagged on watchlist")
    if aml_high:
        flags.append("AML watchlist hit")
    if not bvn_result.get("match") and "error" not in bvn_result:
        flags.append("BVN name mismatch")
    if liveness_val < 0.5:
        flags.append("Liveness check failed")

    if nin_watchlisted or aml_high:
        kyc_status = "blocked"
    elif identity_confidence >= 0.7:
        kyc_status = "verified"
    else:
        kyc_status = "failed"

    # SHA-256 hash before any DB write — never store raw BVN/NIN
    bvn_hash = hashlib.sha256(payload.bvn.encode()).hexdigest()
    nin_hash = hashlib.sha256(payload.nin.encode()).hexdigest()

    user = User(
        bvn_hash=bvn_hash,
        nin_hash=nin_hash,
        phone=payload.phone,
        email=str(payload.email),
        kyc_status=kyc_status,
        identity_confidence=identity_confidence,
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
