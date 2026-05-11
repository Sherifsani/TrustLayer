import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

load_dotenv()

from api.routes import activity, auth, consent, onboard, report, reports, score, score_history, user, webhook
from db.session import SessionLocal

app = FastAPI(title="TrustLayer API", version="1.0.0")

# CORS — open in development, locked to frontend origin in production
_env = os.getenv("ENVIRONMENT", "development")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _env == "development" else ["https://trustlayer.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(onboard.router)
app.include_router(score.router)
app.include_router(report.router)
app.include_router(webhook.router)
app.include_router(consent.router)
app.include_router(user.router)
app.include_router(score_history.router)
app.include_router(activity.router)
app.include_router(reports.router)


@app.get("/")
async def root():
    return {"status": "ok", "service": "TrustLayer API"}


@app.get("/health")
async def health():
    db_status = "unreachable"
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        pass
    finally:
        db.close()
    return {
        "status": "ok" if db_status == "connected" else "degraded",
        "db": db_status,
        "service": "TrustLayer API",
    }
