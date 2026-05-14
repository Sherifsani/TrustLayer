import asyncio
import hashlib
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from fastapi import APIRouter, Depends
from jose import jwt
from sqlalchemy.orm import Session

load_dotenv()

from api.models.db_models import User
from api.models.schemas import OnboardRequest, OnboardResponse
from db.session import get_db
from integrations import dojah
from ml.pipeline import compute_trust_score

SECRET_KEY = os.getenv("SECRET_KEY", "")
ALGORITHM = "HS256"

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

    # Extract individual KYC signal values — degrade gracefully to neutral if any call failed.
    # Each dojah.* function returns the entity dict directly (already unwrapped from the response).

    # BVN: confidence lives in entity.first_name.confidence_value and entity.last_name.confidence_value
    if "error" not in bvn_result:
        fn_conf = bvn_result.get("first_name", {}).get("confidence_value", 50)
        ln_conf = bvn_result.get("last_name", {}).get("confidence_value", 50)
        bvn_confidence = (fn_conf + ln_conf) / 200
    else:
        bvn_confidence = 0.5

    # NIN: sandbox doesn't return watch_listed — defaults to not watchlisted
    nin_entity = nin_result if "error" not in nin_result else {}
    nin_watchlisted = 1 if str(nin_entity.get("watch_listed", "NO")).upper() == "YES" else 0

    # Liveness: entity.face.liveness.{spoof, confidence}
    # spoof=false + high confidence → real person; spoof=true → fake
    if "error" not in liveness_result:
        liveness_data = liveness_result.get("face", {}).get("liveness", {})
        is_spoof = liveness_data.get("spoof", True)
        confidence = liveness_data.get("confidence", 0) / 100
        liveness_score = (1 - confidence) if is_spoof else confidence
    else:
        liveness_score = 0.5

    doc_authentic = 1  # no document uploaded at onboard yet — default to authentic

    # Phone: returns 302 in sandbox so degrades gracefully; entity has first_name directly
    phone_entity = phone_result if "error" not in phone_result else {}
    phone_first = str(phone_entity.get("first_name", "")).upper()
    provided_first = str(payload.first_name).upper()
    phone_name_match = 1 if phone_first and phone_first in provided_first else 0

    # AML: entity.matchResults[] with nameMatchScore — no risk_level field
    aml_entity = aml_result if "error" not in aml_result and isinstance(aml_result, dict) else {}
    match_results = aml_entity.get("matchResults", [])
    if not match_results:
        aml_risk_level = 0
    else:
        max_score = max(m.get("nameMatchScore", 0) for m in match_results)
        aml_risk_level = 2 if max_score >= 85 else 1

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
    bvn_fn_match = bvn_result.get("first_name", {}).get("status", False)
    bvn_ln_match = bvn_result.get("last_name", {}).get("status", False)
    if "error" not in bvn_result and not (bvn_fn_match and bvn_ln_match):
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

    user = User(
        bvn_hash=bvn_hash,
        nin_hash=nin_hash,
        phone=payload.phone,
        email=str(payload.email),
        kyc_status=kyc_status,
        identity_confidence=identity_confidence,
        kyc_signals=kyc_signals,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    await compute_trust_score(str(user.id), business_id="system", db=db)

    token = jwt.encode(
        {"sub": str(user.id), "exp": datetime.utcnow() + timedelta(hours=24)},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    return OnboardResponse(
        user_id=str(user.id),
        kyc_status=kyc_status,
        identity_confidence=round(identity_confidence, 4),
        flags=flags,
        access_token=token,
    )
