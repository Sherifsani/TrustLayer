import os
import uuid

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

load_dotenv()

from api.dependencies import get_current_user, get_db
from api.models.db_models import Report, User
from api.models.schemas import (
    InitiatePaymentRequest,
    InitiatePaymentResponse,
    ReportItem,
    ReportsListResponse,
)
from db.session import get_user
from integrations import squad

router = APIRouter()

REPORT_PRICE_KOBO = 50_000  # ₦500


@router.get("/reports/{user_id}", response_model=ReportsListResponse)
async def list_reports(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if str(user.id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    reports = (
        db.query(Report)
        .filter(Report.user_id == user.id)
        .order_by(Report.created_at.desc())
        .all()
    )

    return ReportsListResponse(
        reports=[
            ReportItem(
                id=str(r.id),
                title=r.title,
                report_type=r.report_type,
                recipient_name=r.recipient_name,
                pages=r.pages,
                status=r.status,
                created_at=r.created_at,
                file_url=r.file_url,
            )
            for r in reports
        ]
    )


@router.post("/report/initiate-payment", response_model=InitiatePaymentResponse)
async def initiate_report_payment(
    payload: InitiatePaymentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = get_user(db, payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if str(user.id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    report = Report(
        user_id=user.id,
        title=_report_title(payload.report_type),
        report_type=payload.report_type,
        recipient_id=payload.recipient_id,
        status="pending",
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    report_id = str(report.id)
    txn_ref = f"report_{report_id}"
    callback_url = os.getenv("SQUAD_WEBHOOK_URL", "")

    result = await squad.initiate_payment(
        amount_kobo=REPORT_PRICE_KOBO,
        email=user.email,
        ref=txn_ref,
        callback_url=callback_url,
    )

    checkout_url = (
        result.get("data", {}).get("checkout_url", "")
        if "error" not in result
        else ""
    )

    return InitiatePaymentResponse(
        report_id=report_id,
        checkout_url=checkout_url,
        txn_ref=txn_ref,
        amount=REPORT_PRICE_KOBO // 100,  # display in naira
    )


def _report_title(report_type: str) -> str:
    from datetime import datetime
    month_year = datetime.utcnow().strftime("%B %Y")
    if report_type == "verified_trust_report":
        return f"Verified Trust Report — {month_year}"
    if report_type == "identity_snapshot":
        return f"Identity & Income Snapshot — {month_year}"
    return f"Report — {month_year}"
