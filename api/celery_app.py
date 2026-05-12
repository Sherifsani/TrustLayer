import asyncio
import os
import uuid as _uuid
from datetime import datetime, timedelta

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("trustlayer", broker=REDIS_URL, backend=REDIS_URL)


def _generate_recommendations(features: dict, score: int, risk: str) -> list:
    recs = []
    if features.get("txn_count_90d", 0) < 10:
        recs.append("Increase your Squad transaction activity to build a stronger payment history.")
    if features.get("txn_failure_rate", 0) > 0.3:
        recs.append("Reduce failed transactions — a high failure rate lowers your score.")
    if features.get("bvn_confidence", 1.0) < 0.7:
        recs.append("Re-verify your BVN to strengthen identity confidence.")
    if features.get("liveness_score", 1.0) < 0.7:
        recs.append("Complete a fresh liveness check to improve your identity score.")
    if features.get("telco_borrow_repaid", 1) == 0:
        recs.append("Repay telco credit on time to build positive credit behaviour.")
    if features.get("topup_frequency", 10) < 4:
        recs.append("Maintain regular airtime top-ups to signal consistent mobile usage.")
    if score >= 75:
        recs.append("Your trust profile is strong — keep up consistent financial behaviour.")
    if not recs:
        recs.append("Continue building your financial history with consistent activity.")
    return recs


def _build_report_content(user_id: str, db) -> dict:
    from api.models.db_models import TrustScore as TrustScoreModel, User
    from db.session import get_user
    from ml.pipeline import compute_trust_score
    from ml.scoring_model import get_shap_details

    result = asyncio.run(compute_trust_score(user_id, business_id="system", db=db))

    raw_features = result.raw_features or {}
    signals = get_shap_details(raw_features) if raw_features else []

    # Score history — last 6 months
    user = get_user(db, user_id)
    resolved_id = user.id if user else None
    history = []
    if resolved_id:
        cutoff = datetime.utcnow() - timedelta(days=180)
        rows = (
            db.query(TrustScoreModel)
            .filter(TrustScoreModel.user_id == resolved_id, TrustScoreModel.computed_at >= cutoff)
            .order_by(TrustScoreModel.computed_at.asc())
            .all()
        )
        history = [{"score": r.score, "computed_at": r.computed_at.isoformat()} for r in rows]

    recommendations = _generate_recommendations(raw_features, result.score, result.risk_level)

    user_name = ""
    if user and user.first_name:
        user_name = f"{user.first_name} {user.last_name or ''}".strip()

    return {
        "score": result.score,
        "risk_level": result.risk_level,
        "recommendation": result.recommendation,
        "reliability_score": result.reliability_score,
        "authenticity_score": result.authenticity_score,
        "drivers": result.drivers,
        "signals": signals,
        "score_history": history,
        "recommendations": recommendations,
        "user_name": user_name,
        "generated_at": datetime.utcnow().isoformat(),
    }


def generate_report_now(report_id: str) -> None:
    from db.session import SessionLocal
    from api.models.db_models import Report

    db = SessionLocal()
    try:
        report = db.query(Report).filter(Report.id == _uuid.UUID(report_id)).first()
        if not report:
            return

        content = _build_report_content(str(report.user_id), db)
        report.content = content
        report.status = "active"
        report.pages = 3
        report.file_url = f"/reports/download/{report_id}"
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def recompute_score_now(user_id: str, business_id: str = "system") -> None:
    from sqlalchemy.orm import Session

    from db.session import SessionLocal
    from ml.pipeline import compute_trust_score

    db: Session = SessionLocal()
    try:
        asyncio.run(compute_trust_score(user_id, business_id=business_id, db=db))
    finally:
        db.close()


@celery_app.task(name="recompute_score")
def recompute_score(user_id: str, business_id: str = "system") -> None:
    recompute_score_now(user_id, business_id=business_id)


@celery_app.task(name="generate_report")
def generate_report(report_id: str) -> None:
    generate_report_now(report_id)
