import asyncio
import os
import uuid
import logging

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

load_dotenv()

logger = logging.getLogger(__name__)

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


def _report_download_url(report_id: str) -> str:
    return f"/reports/download/{report_id}"


def _render_report_document(report: Report) -> bytes:
    content = report.content
    if not content:
        # Fallback for reports generated before rich content was introduced
        try:
            trust_score = report.user.trust_scores[0].score if report.user and report.user.trust_scores else None
        except Exception:
            trust_score = None
        content = {
            "score": trust_score,
            "risk_level": "unknown",
            "recommendation": "N/A",
            "reliability_score": 0,
            "authenticity_score": 0,
            "drivers": [],
            "signals": [],
            "score_history": [],
            "recommendations": ["Report data unavailable — please regenerate."],
            "user_name": "",
            "generated_at": "",
        }

    return _render_rich_pdf(report, content)


def _render_rich_pdf(report: Report, content: dict) -> bytes:
    import io
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
    )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    W = A4[0] - 40 * mm  # usable width

    # Custom styles
    brand_blue = colors.HexColor("#1E3A5F")
    low_green = colors.HexColor("#16A34A")
    med_amber = colors.HexColor("#D97706")
    high_red = colors.HexColor("#DC2626")
    light_bg = colors.HexColor("#F8FAFC")
    mid_grey = colors.HexColor("#64748B")

    risk_colors = {"low": low_green, "medium": med_amber, "high": high_red, "blocked": high_red}
    risk_color = risk_colors.get(content.get("risk_level", ""), mid_grey)

    h1 = ParagraphStyle("H1", parent=styles["Heading1"], textColor=brand_blue, fontSize=20, spaceAfter=4)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], textColor=brand_blue, fontSize=13, spaceAfter=4, spaceBefore=12)
    body = ParagraphStyle("Body", parent=styles["Normal"], fontSize=9, leading=13)
    caption = ParagraphStyle("Caption", parent=styles["Normal"], fontSize=8, textColor=mid_grey, leading=11)
    score_style = ParagraphStyle("Score", parent=styles["Normal"], fontSize=44, textColor=brand_blue, leading=50)
    risk_style = ParagraphStyle("Risk", parent=styles["Normal"], fontSize=13, textColor=risk_color, leading=16)

    story = []

    # ── Header ──────────────────────────────────────────────────────────────────
    story.append(Paragraph("TrustLayer", h1))
    story.append(Paragraph(report.title, ParagraphStyle("Sub", parent=styles["Normal"], fontSize=11, textColor=mid_grey)))
    user_name = content.get("user_name") or ""
    gen_at = content.get("generated_at", "")[:10]
    story.append(Paragraph(f"Prepared for: <b>{user_name or 'User'}</b> &nbsp;·&nbsp; Generated: {gen_at}", caption))
    story.append(HRFlowable(width=W, thickness=1.5, color=brand_blue, spaceAfter=10))

    # ── Score Summary ────────────────────────────────────────────────────────────
    story.append(Paragraph("Trust Score Summary", h2))

    score_val = content.get("score")
    risk_label = (content.get("risk_level") or "").upper()
    rec_label = (content.get("recommendation") or "").capitalize()
    auth = content.get("authenticity_score", 0)
    rel = content.get("reliability_score", 0)

    summary_data = [
        [
            Paragraph(str(score_val) if score_val is not None else "—", score_style),
            Table(
                [
                    [Paragraph(f"Risk Level", caption), Paragraph(f"<b>{risk_label}</b>", risk_style)],
                    [Paragraph(f"Recommendation", caption), Paragraph(f"<b>{rec_label}</b>", body)],
                    [Paragraph(f"Identity Authenticity", caption), Paragraph(f"<b>{auth}/100</b>", body)],
                    [Paragraph(f"Payment Reliability", caption), Paragraph(f"<b>{rel}/100</b>", body)],
                ],
                colWidths=[W * 0.25, W * 0.4],
                style=TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 4)]),
            ),
        ]
    ]
    summary_table = Table(summary_data, colWidths=[W * 0.25, W * 0.75])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), light_bg),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(summary_table)

    # Top drivers
    drivers = content.get("drivers") or []
    if drivers:
        story.append(Spacer(1, 6))
        story.append(Paragraph("Key Score Drivers", ParagraphStyle("DrH", parent=styles["Normal"], fontSize=9, textColor=mid_grey)))
        for d in drivers:
            story.append(Paragraph(f"• {d}", body))

    # ── Signal Breakdown ─────────────────────────────────────────────────────────
    signals = content.get("signals") or []
    if signals:
        story.append(Paragraph("Signal-by-Signal Breakdown", h2))
        story.append(Paragraph("Each signal's contribution to your trust score, ranked by impact.", caption))
        story.append(Spacer(1, 4))

        rows = [[
            Paragraph("<b>Signal</b>", caption),
            Paragraph("<b>Value</b>", caption),
            Paragraph("<b>Contribution</b>", caption),
        ]]
        for s in signals:
            contrib = s.get("contribution", 0)
            direction = s.get("direction", "positive")
            bar_color = low_green if direction == "positive" else high_red
            prefix = "+" if contrib >= 0 else ""
            contrib_text = Paragraph(
                f'<font color="{"#16A34A" if contrib >= 0 else "#DC2626"}"><b>{prefix}{contrib} pts</b></font>',
                body,
            )
            rows.append([
                Paragraph(s.get("display_name", s.get("feature", "")), body),
                Paragraph(str(s.get("value", "")), body),
                contrib_text,
            ])

        sig_table = Table(rows, colWidths=[W * 0.5, W * 0.2, W * 0.3])
        sig_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), light_bg),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light_bg]),
        ]))
        story.append(sig_table)

    # ── Score History ────────────────────────────────────────────────────────────
    history = content.get("score_history") or []
    if history:
        story.append(Paragraph("6-Month Score History", h2))
        h_rows = [[Paragraph("<b>Date</b>", caption), Paragraph("<b>Score</b>", caption)]]
        for h in history[-12:]:  # cap at 12 rows to keep it tidy
            date_str = (h.get("computed_at") or "")[:10]
            h_rows.append([Paragraph(date_str, body), Paragraph(str(h.get("score", "")), body)])
        hist_table = Table(h_rows, colWidths=[W * 0.5, W * 0.5])
        hist_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), light_bg),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light_bg]),
        ]))
        story.append(hist_table)

    # ── Recommendations ──────────────────────────────────────────────────────────
    recs = content.get("recommendations") or []
    if recs:
        story.append(Paragraph("Recommendations", h2))
        for i, rec in enumerate(recs, 1):
            story.append(Paragraph(f"{i}. {rec}", body))

    # ── Footer ───────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width=W, thickness=0.5, color=colors.HexColor("#CBD5E1")))
    story.append(Paragraph(
        "Generated by TrustLayer · AI-Powered Trust Scoring for Nigerian Fintechs · Hackathon Demo",
        caption,
    ))

    doc.build(story)
    return buffer.getvalue()


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
        .filter(Report.user_id == user.id, Report.status == "active")
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
                file_url=r.file_url or _report_download_url(str(r.id)),
            )
            for r in reports
        ]
    )


@router.get("/reports/download/{report_id}")
async def download_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        report_uuid = uuid.UUID(report_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid report_id format")

    report = db.query(Report).filter(Report.id == report_uuid).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if report.status != "active":
        raise HTTPException(status_code=409, detail="Report is not ready yet")

    payload = _render_report_document(report)
    filename = f"trustlayer-report-{report_id}.pdf"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=payload, media_type="application/pdf", headers=headers)


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
        recipient_name=payload.recipient_id,
        status="active",
        pages=3,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    report_id = str(report.id)
    txn_ref = f"report_{report_id}"
    logger.info(f"Generating report {report_id} for user {user.email}")

    # Populate content in background — report is already "active" so it shows immediately
    try:
        from api.celery_app import generate_report_now
        await asyncio.to_thread(generate_report_now, report_id)
    except Exception as e:
        logger.error(f"Report generation failed for {report_id}: {e}")

    # Initiate Squad payment (non-blocking — report is already active above)
    checkout_url = ""
    try:
        result = await squad.initiate_payment(
            amount_kobo=50_000,
            email=user.email,
            ref=txn_ref,
            callback_url=os.getenv("SQUAD_WEBHOOK_URL", ""),
        )
        checkout_url = (
            result.get("data", {}).get("checkout_url", "")
            or result.get("checkout_url", "")
            or result.get("link", "")
        )
        if checkout_url:
            logger.info(f"Squad checkout URL for {txn_ref}: {checkout_url}")
        else:
            logger.warning(f"Squad returned no checkout_url for {txn_ref}: {result}")
    except Exception as e:
        logger.error(f"Squad payment initiation failed for {report_id}: {e}")

    if not checkout_url and os.getenv("ENVIRONMENT") == "development":
        checkout_url = f"https://sandbox-pay.squadco.com/?ref={txn_ref}"

    return InitiatePaymentResponse(
        report_id=report_id,
        checkout_url=checkout_url,
        txn_ref=txn_ref,
        amount=500,
    )


@router.get("/reports/view/{report_id}")
async def view_report_content(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        report_uuid = uuid.UUID(report_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid report_id format")

    report = db.query(Report).filter(Report.id == report_uuid).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if report.status != "active":
        raise HTTPException(status_code=409, detail="Report is not active yet")

    return {
        "report_id": report_id,
        "title": report.title,
        "recipient_name": report.recipient_name,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "content": report.content or {},
    }


def _report_title(report_type: str) -> str:
    from datetime import datetime
    month_year = datetime.utcnow().strftime("%B %Y")
    if report_type == "verified_trust_report":
        return f"Verified Trust Report — {month_year}"
    if report_type == "identity_snapshot":
        return f"Identity & Income Snapshot — {month_year}"
    return f"Report — {month_year}"


@router.post("/report/test-payment-webhook")
async def test_payment_webhook(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    DEV ONLY: Simulate a Squad webhook for testing report generation.
    
    Usage: POST /report/test-payment-webhook?report_id=<uuid>
    This simulates the webhook that would come from Squad when payment succeeds.
    """
    if os.getenv("ENVIRONMENT") != "development":
        raise HTTPException(status_code=403, detail="Only available in development")
    
    try:
        report_uuid = uuid.UUID(report_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid report_id format")
    
    report = db.query(Report).filter(Report.id == report_uuid).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if report.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    logger.info(f"Test payment webhook: simulating payment for report {report_id}")
    
    # Mark report as generating
    report.status = "generating"
    report.file_url = _report_download_url(report_id)
    db.commit()
    
    # Dispatch generation task
    try:
        from api.celery_app import generate_report, generate_report_now
        if os.getenv("REDIS_URL"):
            generate_report.delay(report_id)
            logger.info(f"Test payment webhook: dispatched generate_report task for {report_id}")
        else:
            generate_report_now(report_id)
            logger.info(f"Test payment webhook: generated report inline for {report_id}")
    except Exception as e:
        logger.error(f"Test payment webhook: failed to dispatch task: {e}")
        try:
            from api.celery_app import generate_report_now
            generate_report_now(report_id)
        except Exception as inner_e:
            logger.error(f"Test payment webhook: inline generation failed: {inner_e}")
    
    # Recompute user's score
    try:
        from api.celery_app import recompute_score, recompute_score_now
        if os.getenv("REDIS_URL"):
            recompute_score.delay(str(current_user.id), business_id="system")
        else:
            recompute_score_now(str(current_user.id), business_id="system")
    except Exception as e:
        logger.error(f"Test payment webhook: failed to recompute score: {e}")
    
    return {
        "status": "ok",
        "message": "Test payment webhook processed",
        "report_id": report_id,
        "report_status": "generating"
    }
