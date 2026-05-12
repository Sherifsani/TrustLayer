from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_db
from api.models.db_models import Consent, User
from api.models.schemas import ConsentRequest, ConsentResponse

router = APIRouter()


@router.post("/consent", response_model=ConsentResponse)
async def upsert_consent(
    payload: ConsentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_id = str(current_user.id)
    record = (
        db.query(Consent)
        .filter(Consent.user_id == current_user.id, Consent.business_id == payload.business_id)
        .first()
    )

    if payload.action == "revoke":
        if record:
            record.revoked = True
            db.commit()
            db.refresh(record)
            return _to_response(user_id, record)
        return ConsentResponse(
            user_id=user_id,
            business_id=payload.business_id,
            granted_signals=[],
            denied_signals=[],
            revoked=True,
        )

    expires_at = datetime.utcnow() + timedelta(days=payload.expires_days)

    if record:
        record.granted_signals = payload.signals
        record.denied_signals = []
        record.revoked = False
        record.expires_at = expires_at
        record.granted_at = datetime.utcnow()
    else:
        record = Consent(
            user_id=current_user.id,
            business_id=payload.business_id,
            granted_signals=payload.signals,
            denied_signals=[],
            expires_at=expires_at,
        )
        db.add(record)

    db.commit()
    db.refresh(record)
    return _to_response(user_id, record)


@router.get("/consent/{user_id}", response_model=List[ConsentResponse])
async def get_consents(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if str(current_user.id) != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    from uuid import UUID
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    now = datetime.utcnow()
    records = (
        db.query(Consent)
        .filter(
            Consent.user_id == user_uuid,
            Consent.revoked == False,
        )
        .all()
    )
    # Filter out expired records in Python to handle nullable expires_at cleanly
    active = [r for r in records if r.expires_at is None or r.expires_at > now]
    return [_to_response(user_id, r) for r in active]


def _to_response(user_id: str, record: Consent) -> ConsentResponse:
    return ConsentResponse(
        user_id=user_id,
        business_id=record.business_id,
        granted_signals=record.granted_signals or [],
        denied_signals=record.denied_signals or [],
        revoked=record.revoked,
    )
