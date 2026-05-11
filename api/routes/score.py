from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.dependencies import get_business_api_key, get_db
from api.models.schemas import ScoreRequest, ScoreResponse
from db.session import get_user
from ml.pipeline import compute_trust_score

router = APIRouter()


@router.post("/score", response_model=ScoreResponse)
async def score(
    payload: ScoreRequest,
    db: Session = Depends(get_db),
    business_id: str = Depends(get_business_api_key),
):
    user = get_user(db, payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Short-circuit blocked users without touching the ML pipeline
    if user.kyc_status == "blocked":
        return ScoreResponse(
            trust_score=0,
            risk_level="blocked",
            recommendation="decline",
            drivers=["User is blocked due to KYC/AML failure"],
            signals_used=[],
        )

    result = await compute_trust_score(payload.user_id, business_id, db)
    return ScoreResponse(
        trust_score=result.score,
        risk_level=result.risk_level,
        recommendation=result.recommendation,
        drivers=result.drivers,
        signals_used=result.signals_used,
    )
