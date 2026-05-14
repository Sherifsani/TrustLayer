from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_db
from api.models.db_models import User
from api.models.schemas import CreditProfileResponse, UserProfileResponse
from db.session import get_user
from integrations.mono import fetch_account_income, fetch_account_statement
from ml.credit_scoring import calculate_trust_score, summarize_financial_signals

router = APIRouter()


@router.get("/user/{user_id}", response_model=UserProfileResponse)
async def get_user_profile(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if str(user.id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    return UserProfileResponse(
        user_id=user.user_handle or str(user.id),
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        phone=user.phone,
        location=user.location,
        kyc_status=user.kyc_status,
        identity_confidence=user.identity_confidence,
        joined=user.created_at,
        # BVN/NIN are SHA-256 hashed at ingestion — real digits unrecoverable
        nin_masked="•••• •••• ****",
        bvn_masked="•••• •••• ****",
    )


@router.get("/api/user/credit-profile", response_model=CreditProfileResponse)
async def get_credit_profile(
    user_id: Optional[str] = None,
    user_handle: Optional[str] = None,
    db: Session = Depends(get_db),
):
    lookup = user_id or user_handle or "usr_adaeze001"
    user = get_user(db, lookup)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.mono_account_id:
        raise HTTPException(status_code=400, detail="User has no linked Mono account")

    try:
        statement_payload = fetch_account_statement(user.mono_account_id)
        income_payload = fetch_account_income(user.mono_account_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch Mono data: {exc}")

    signals = summarize_financial_signals(statement_payload, income_payload)
    score_data = calculate_trust_score(
        transaction_volume=signals["transaction_volume"],
        income_consistency=signals["income_consistency"],
        avg_monthly_balance=signals["avg_monthly_balance"],
    )

    return CreditProfileResponse(
        user_id=user.user_handle or str(user.id),
        mono_account_id=user.mono_account_id,
        trust_score=int(score_data["trust_score"]),
        signals=signals,
        component_scores={
            "transaction_volume_score": float(score_data["transaction_volume_score"]),
            "income_consistency_score": float(score_data["income_consistency_score"]),
            "avg_balance_score": float(score_data["avg_balance_score"]),
        },
        statement_source=str(statement_payload.get("source", "unknown")),
        income_source=str(income_payload.get("source", "unknown")),
    )
