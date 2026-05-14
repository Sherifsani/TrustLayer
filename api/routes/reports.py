import io
import os
import uuid

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

load_dotenv()

from api.dependencies import get_current_user, get_db
from api.models.db_models import Report, TrustScore, User
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

    if "error" in result:
        raise HTTPException(status_code=502, detail=f"Squad payment initiation failed: {result['error']}")

    # Squad returns transaction_ref in data; checkout URL is constructed from it
    squad_base = os.getenv("SQUAD_BASE_URL", "https://sandbox-api-d.squadco.com")
    checkout_host = squad_base.replace("sandbox-api-d.", "sandbox-checkout.").replace("api.", "checkout.")
    checkout_url = f"{checkout_host}?transaction_ref={txn_ref}"

    return InitiatePaymentResponse(
        report_id=report_id,
        checkout_url=checkout_url,
        txn_ref=txn_ref,
        amount=REPORT_PRICE_KOBO // 100,
    )


@router.get("/report/download/{report_id}")
async def download_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        rid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report ID")

    report = db.query(Report).filter(Report.id == rid).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if str(report.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    if report.status != "ready":
        raise HTTPException(status_code=402, detail="Report not ready yet")

    latest_score = (
        db.query(TrustScore)
        .filter(TrustScore.user_id == current_user.id)
        .order_by(TrustScore.computed_at.desc())
        .first()
    )

    pdf_bytes = _build_pdf(current_user, report, latest_score)

    filename = f"TrustLayer_Report_{report_id[:8]}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _build_pdf(user: User, report: Report, score: TrustScore | None) -> bytes:
    from datetime import datetime
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Header bar
    pdf.set_fill_color(15, 23, 42)
    pdf.rect(0, 0, 210, 28, "F")
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(14, 8)
    pdf.cell(0, 10, "TrustLayer", ln=False)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_xy(14, 19)
    pdf.cell(0, 5, "Verified Identity & Trust Report", ln=True)
    pdf.set_text_color(0, 0, 0)

    pdf.set_y(36)

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, _s(report.title), ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, f"Generated: {datetime.utcnow().strftime('%d %B %Y, %H:%M UTC')}   |   Report ID: {str(report.id)[:8].upper()}", ln=True)
    pdf.ln(6)

    # Section: Identity
    pdf.set_text_color(0, 0, 0)
    _section_header(pdf, "Identity Summary")
    display_name = " ".join(filter(None, [user.first_name, user.last_name])) or "-"
    _row(pdf, "Full name", _s(display_name))
    _row(pdf, "Email", _s(user.email))
    _row(pdf, "Phone", _s(user.phone or "-"))
    _row(pdf, "KYC status", _s((user.kyc_status or "-").capitalize()))
    _row(pdf, "Identity confidence", f"{round((user.identity_confidence or 0) * 100)}%")
    pdf.ln(4)

    # Section: Trust Score
    _section_header(pdf, "Trust Score")
    if score:
        _row(pdf, "Score", f"{score.score} / 100")
        _row(pdf, "Risk level", score.risk_level.capitalize())
        _row(pdf, "Computed at", score.computed_at.strftime("%d %b %Y %H:%M UTC"))
        pdf.ln(2)
        if score.drivers:
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(0, 6, "Key drivers:", ln=True)
            pdf.set_font("Helvetica", "", 9)
            for d in score.drivers:
                pdf.cell(6)
                pdf.cell(0, 5, _s(f"- {d}"), ln=True)
    else:
        _row(pdf, "Score", "Not yet computed")
    pdf.ln(4)

    # Section: Verification checks
    _section_header(pdf, "Verification Checks")
    signals = user.kyc_signals or {}
    checks = [
        ("BVN identity match", signals.get("bvn_confidence", 0) >= 0.5),
        ("NIN watchlist clear", signals.get("nin_watchlisted", 0) == 0),
        ("Liveness check passed", signals.get("liveness_score", 0) >= 0.5),
        ("Phone name match", signals.get("phone_name_match", 0) == 1),
        ("AML screening clear", signals.get("aml_risk_level", 0) < 2),
    ]
    for label, passed in checks:
        mark = "PASS" if passed else "FAIL"
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(90, 6, label)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(0, 150, 80) if passed else pdf.set_text_color(200, 50, 50)
        pdf.cell(0, 6, mark, ln=True)
        pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    # Footer
    pdf.set_y(-20)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 5, "This report is generated by TrustLayer. Powered by Dojah KYC + Squad payments.", ln=True, align="C")

    return pdf.output()


def _s(text: str) -> str:
    """Strip characters that can't be encoded in latin-1 (fpdf2 core fonts)."""
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _section_header(pdf: "FPDF", title: str) -> None:
    pdf.set_fill_color(240, 242, 245)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 7, f"  {title}", ln=True, fill=True)
    pdf.ln(2)


def _row(pdf: "FPDF", label: str, value: str) -> None:
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(55, 6, label)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 6, value, ln=True)


def _report_title(report_type: str) -> str:
    from datetime import datetime
    month_year = datetime.utcnow().strftime("%B %Y")
    if report_type == "verified_trust_report":
        return f"Verified Trust Report — {month_year}"
    if report_type == "identity_snapshot":
        return f"Identity & Income Snapshot — {month_year}"
    return f"Report — {month_year}"
