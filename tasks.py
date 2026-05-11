# Backwards-compatible re-export — canonical definition lives in api/celery_app.py
from api.celery_app import celery_app, recompute_score

__all__ = ["celery_app", "recompute_score"]
