from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_db
from api.models.db_models import SquadEvent, TrustScore, User
from api.models.schemas import ReportResponse

router = APIRouter()


@router.get("/report/{user_id}", response_model=ReportResponse)
async def get_report(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Users can only fetch their own report
    if str(current_user.id) != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    unlock = (
        db.query(SquadEvent)
        .filter(
            SquadEvent.user_id == user_id,
            SquadEvent.txn_type == "report_unlock",
            SquadEvent.status == "Success",
        )
        .first()
    )
    if not unlock:
        raise HTTPException(status_code=402, detail="Report not unlocked — payment required")

    latest = (
        db.query(TrustScore)
        .filter(TrustScore.user_id == user_id)
        .order_by(TrustScore.computed_at.desc())
        .first()
    )
    if not latest:
        raise HTTPException(status_code=404, detail="No trust score found for user")

    return ReportResponse(
        user_id=user_id,
        trust_score=latest.score,
        risk_level=latest.risk_level,
        drivers=latest.drivers,
        signals_used=latest.signals_used,
        computed_at=latest.computed_at.isoformat(),
    )
