import os

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("trustlayer", broker=REDIS_URL, backend=REDIS_URL)


@celery_app.task(name="recompute_score")
def recompute_score(user_id: str, business_id: str = "system") -> None:
    import asyncio

    from sqlalchemy.orm import Session

    from db.session import SessionLocal
    from ml.pipeline import compute_trust_score

    db: Session = SessionLocal()
    try:
        asyncio.run(compute_trust_score(user_id, business_id=business_id, db=db))
    finally:
        db.close()
