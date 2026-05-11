from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from api.models.db_models import TrustScore as TrustScoreModel, Consent, SquadEvent, User
from api.models.schemas import TrustScoreResult
from db.session import get_user
from integrations import mono
from ml import scoring_model, anomaly_detector


def _risk_level(score: int) -> str:
    if score >= 75:
        return "low"
    elif score >= 50:
        return "medium"
    else:
        return "high"


def _recommendation(risk: str) -> str:
    return {
        "low": "approve",
        "medium": "review",
        "high": "decline",
        "blocked": "decline",
    }[risk]


def _collect_squad_features(squad_events: list) -> dict:
    if not squad_events:
        return {
            "txn_count_90d": 0.5,
            "avg_txn_amount": 0.5,
            "txn_failure_rate": 0.5,
            "channel_diversity": 0.5,
            "dispute_count": 0,
            "bounce_count_90d": 0.5,
        }

    cutoff = datetime.utcnow() - timedelta(days=90)
    recent = [e for e in squad_events if e.created_at >= cutoff]

    if not recent:
        return {
            "txn_count_90d": 0,
            "avg_txn_amount": 0.5,
            "txn_failure_rate": 0.5,
            "channel_diversity": 0.5,
            "dispute_count": 0,
            "bounce_count_90d": 0.5,
        }

    amounts_naira = [e.amount / 100 for e in recent]
    statuses = [e.status for e in recent]

    return {
        "txn_count_90d": len(recent),
        "avg_txn_amount": sum(amounts_naira) / len(amounts_naira),
        "txn_failure_rate": statuses.count("Failed") / len(statuses),
        "channel_diversity": len({e.txn_type for e in recent}),
        "dispute_count": 0,       # disputes table not yet built
        "bounce_count_90d": 0.5,  # no bounce signal yet
    }


async def compute_trust_score(user_id: str, business_id: str, db: Session) -> TrustScoreResult:
    # 1. Resolve handle or UUID → actual User row so FK writes always use real UUID
    user = get_user(db, user_id)
    resolved_id = user.id if user else user_id  # fall back to string only if user not found

    # 2. Load SquadEvent records and compute transaction features
    squad_events = db.query(SquadEvent).filter(SquadEvent.user_id == resolved_id).all()
    squad_features = _collect_squad_features(squad_events)

    # 3. Telco features (mocked via Mono)
    phone = user.phone if user else ""
    telco = mono.get_telco_data(phone)
    telco_features = {
        "topup_frequency": telco["topup_count_30d"],
        "telco_borrow_repaid": int(telco["borrow_repaid_ontime"]),
    }

    # 4. KYC features — read from stored kyc_signals, fall back to neutral if not yet onboarded
    kyc = (user.kyc_signals or {}) if user else {}
    kyc_features = {
        "bvn_confidence":   kyc.get("bvn_confidence", 0.5),
        "nin_watchlisted":  kyc.get("nin_watchlisted", 0),
        "liveness_score":   kyc.get("liveness_score", 0.5),
        "doc_authentic":    kyc.get("doc_authentic", 1),
        "phone_name_match": kyc.get("phone_name_match", 0.5),
        "aml_risk_level":   kyc.get("aml_risk_level", 0),
    }

    features: dict = {}
    features.update(squad_features)
    features.update(telco_features)
    features.update(kyc_features)
    features.setdefault("income_stability", 0.5)

    signals_used = ["telco_data"]
    if squad_events:
        signals_used.append("squad_history")
    if user and user.kyc_signals:
        signals_used.append("kyc")

    # 5. Hard rules — return early if blocked
    if kyc_features["nin_watchlisted"] == 1:
        return _save_and_return(
            db, resolved_id, score=0, risk="blocked",
            drivers=["NIN watchlist status → blocked"],
            signals_used=signals_used,
        )
    if kyc_features["aml_risk_level"] == 2:
        return _save_and_return(
            db, resolved_id, score=0, risk="blocked",
            drivers=["AML risk screening → blocked"],
            signals_used=signals_used,
        )

    # 6. Base score from GradientBoostingClassifier
    base_score = scoring_model.predict_score(features)

    # Liveness hard cap (doesn't block — caps at 20)
    if kyc_features["liveness_score"] < 0.5:
        base_score = min(base_score, 20.0)

    # 7. Anomaly detector — 0.7 multiplier if unusual pattern detected
    is_anomaly, anomaly_msg = anomaly_detector.check_anomaly(features)
    final_score = base_score * 0.7 if is_anomaly else base_score

    # 8. SHAP drivers
    drivers = scoring_model.explain_score(features)
    if is_anomaly and anomaly_msg:
        drivers.append(anomaly_msg)
    if not drivers:
        drivers = ["Insufficient data to generate explanation"]

    # 9–10. Risk level and recommendation
    final_score = max(0, min(100, round(final_score)))
    risk = _risk_level(final_score)

    return _save_and_return(
        db, resolved_id, score=final_score, risk=risk,
        drivers=drivers, signals_used=signals_used,
    )


def _save_and_return(
    db: Session,
    user_id: str,
    score: int,
    risk: str,
    drivers: list,
    signals_used: list,
) -> TrustScoreResult:
    now = datetime.utcnow()
    record = TrustScoreModel(
        user_id=user_id,
        score=score,
        risk_level=risk,
        drivers=drivers,
        signals_used=signals_used,
        computed_at=now,
    )
    db.add(record)
    db.commit()

    return TrustScoreResult(
        user_id=str(user_id),
        score=score,
        risk_level=risk,
        recommendation=_recommendation(risk),
        drivers=drivers,
        signals_used=signals_used,
        computed_at=now,
    )
