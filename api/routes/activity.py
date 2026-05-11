import hashlib

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_db
from api.models.db_models import Consent, SquadEvent, User
from api.models.schemas import ActivityEvent, ActivityResponse
from db.session import get_user

router = APIRouter()

TXN_DESCRIPTIONS = {
    "Card":           ("Card payment processed",   "squad"),
    "Transfer":       ("Bank transfer logged",     "squad"),
    "Bank":           ("Bank transaction logged",  "squad"),
    "Ussd":           ("USSD payment logged",      "squad"),
    "VirtualAccount": ("Virtual account credit",   "squad"),
}


def _txn_score_impact(txn_ref: str, status: str) -> int:
    seed = int(hashlib.md5(txn_ref.encode()).hexdigest(), 16)
    if status == "Success":
        return (seed % 4) + 2      # +2 to +5
    return -((seed % 3) + 3)       # -3 to -5


@router.get("/activity/{user_id}", response_model=ActivityResponse)
async def get_activity(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if str(user.id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    squad_events = (
        db.query(SquadEvent)
        .filter(SquadEvent.user_id == user.id)
        .order_by(SquadEvent.created_at.desc())
        .limit(50)
        .all()
    )

    consent_records = (
        db.query(Consent)
        .filter(Consent.user_id == user.id)
        .order_by(Consent.granted_at.desc())
        .all()
    )

    events: list[ActivityEvent] = []

    for e in squad_events:
        desc, source = TXN_DESCRIPTIONS.get(e.txn_type, ("Transaction logged", "squad"))
        events.append(ActivityEvent(
            id=f"evt_{str(e.id)[:8]}",
            description=desc,
            source=source.upper() if source == "squad" else source,
            source_type="transaction",
            timestamp=e.created_at,
            score_impact=_txn_score_impact(e.txn_ref, e.status),
            type="transaction",
        ))

    for c in consent_records:
        action = "revoked from" if c.revoked else "granted to"
        events.append(ActivityEvent(
            id=f"con_{str(c.id)[:8]}",
            description=f"Consent {action} {c.business_id}",
            source="Consent",
            source_type="consent",
            timestamp=c.granted_at,
            score_impact=None,
            type="consent",
        ))

    events.sort(key=lambda e: e.timestamp, reverse=True)

    return ActivityResponse(user_id=user_id, events=events)
