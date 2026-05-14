import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.dependencies import get_business_api_key, get_db
from api.models.db_models import TrustScore
from api.models.schemas import OrgDisburseRequest, OrgDisburseResponse
from db.session import get_user
from integrations import squad

router = APIRouter()


@router.post("/org/disburse", response_model=OrgDisburseResponse)
async def org_disburse(
    payload: OrgDisburseRequest,
    db: Session = Depends(get_db),
    business_id: str = Depends(get_business_api_key),
):
    user = get_user(db, payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    latest = (
        db.query(TrustScore)
        .filter(TrustScore.user_id == user.id)
        .order_by(TrustScore.computed_at.desc())
        .first()
    )

    if not latest:
        raise HTTPException(status_code=422, detail="No trust score on record — run POST /score first")

    if latest.risk_level in ("high", "blocked"):
        return OrgDisburseResponse(
            status="blocked",
            message=f"Transfer blocked — applicant risk level is {latest.risk_level}.",
            risk_level=latest.risk_level,
        )

    transfer_ref = f"disburse_{business_id}_{uuid.uuid4().hex[:10]}"

    result = await squad.transfer(
        bank_code=payload.bank_code,
        account_number=payload.account_number,
        amount_kobo=payload.amount_kobo,
        ref=transfer_ref,
    )

    if "error" in result:
        return OrgDisburseResponse(
            status="failed",
            message=f"Squad transfer failed: {result['error']}",
            risk_level=latest.risk_level,
        )

    return OrgDisburseResponse(
        status="approved",
        message=f"Transfer of ₦{payload.amount_kobo // 100:,} initiated successfully.",
        transfer_ref=transfer_ref,
        risk_level=latest.risk_level,
    )
