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


@celery_app.task(name="generate_report")
def generate_report(report_id: str) -> None:
    import time
    import uuid as _uuid

    from db.session import SessionLocal
    from api.models.db_models import Report

    time.sleep(3)  # simulate generation

    db = SessionLocal()
    try:
        report = db.query(Report).filter(Report.id == _uuid.UUID(report_id)).first()
        if report:
            report.status = "ready"
            report.file_url = f"/report/download/{report_id}"
            db.commit()
    finally:
        db.close()
