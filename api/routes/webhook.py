import json
import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from api.models.db_models import SquadEvent, User
from api.models.schemas import SquadWebhookPayload
from db.session import get_db
from integrations.squad import validate_webhook_signature

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/webhook/squad")
async def squad_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    raw_body = await request.body()
    signature = request.headers.get("x-squad-encrypted-body", "")

    # Always return 200 to Squad — never let them retry indefinitely
    if not validate_webhook_signature(raw_body, signature):
        logger.warning("Squad webhook: invalid signature — ignoring payload")
        return {"status": "ok"}

    try:
        payload = SquadWebhookPayload.model_validate(json.loads(raw_body))
    except Exception as exc:
        logger.warning("Squad webhook: failed to parse body — %s", exc)
        return {"status": "ok"}

    # Only process successful charge events
    if payload.Event != "charge_successful":
        return {"status": "ok"}
    if payload.Body.transaction_status != "Success":
        return {"status": "ok"}

    user = db.query(User).filter(User.email == payload.Body.email).first()
    if not user:
        logger.info("Squad webhook: no user found for email %s", payload.Body.email)
        return {"status": "ok"}

    event = SquadEvent(
        user_id=user.id,
        txn_ref=payload.Body.transaction_ref,
        amount=payload.Body.amount,
        txn_type=payload.Body.transaction_type,
        status=payload.Body.transaction_status,
    )
    db.add(event)
    db.commit()

    # Fire-and-forget score recompute — never block the webhook response
    from api.celery_app import recompute_score
    recompute_score.delay(str(user.id), business_id="system")

    return {"status": "ok"}
