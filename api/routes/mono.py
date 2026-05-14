import json
import urllib.parse
import os
from typing import Optional
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from db.session import get_db, get_user
from integrations.mono import create_connect_session, exchange_code_for_account, verify_webhook_signature
from api.models.db_models import User

router = APIRouter()


class CreateSessionRequest(BaseModel):
    user_id: Optional[str] = None
    user_handle: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None


class ExchangeTokenRequest(BaseModel):
    code: str
    user_id: Optional[str] = None
    user_handle: Optional[str] = None


@router.post("/mono/create-session")
async def create_session(req: CreateSessionRequest):
    # Accept either user_id or user_handle for demo convenience
    # No DB dependency — use provided name/email as-is
    name = req.name or "Demo User"
    email = req.email or "demo@trustlayer.demo"

    session = create_connect_session(name=name, email=email)
    return session


@router.post("/mono/exchange-token")
async def exchange_token(req: ExchangeTokenRequest, db: Session = Depends(get_db)):
    code = req.code
    user_id = req.user_id or req.user_handle
    if not code or not user_id:
        raise HTTPException(status_code=400, detail="code and user_id/user_handle required")

    try:
        result = exchange_code_for_account(code)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"failed to exchange code: {exc}")
    account_id = result.get("account_id")
    if not account_id:
        raise HTTPException(status_code=502, detail="failed to exchange code")

    try:
        user = get_user(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="user not found")

        user.mono_account_id = account_id
        db.add(user)
        db.commit()
        db.refresh(user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"database error: {str(e)}")

    return {
        "status": "ok",
        "account_id": account_id,
        "user_id": user.user_handle or str(user.id),
    }


@router.get("/mock-mono-widget", response_class=HTMLResponse)
async def mock_mono_widget(session_id: str = "", name: str = "Demo", email: str = "demo@trustlayer.demo"):
    # Very small mock page that simulates the Mono Connect widget for local dev.
    # It will redirect to the frontend /mono-callback with a code and close behavior.
    frontend_base = os.getenv("FRONTEND_BASE_URL", "http://127.0.0.1:5173")
    params = urllib.parse.urlencode({"code": f"MOCKCODE_{session_id}", "name": name, "email": email})
    approve_link = f"{frontend_base}/mono-callback?{params}"
    html = f"""
    <html>
      <head><title>Mock Mono Widget</title></head>
      <body style='font-family: system-ui, sans-serif; display:flex; align-items:center; justify-content:center; height:100vh;'>
        <div style='max-width:420px;text-align:center'>
          <h2>Mock Mono Connect</h2>
          <p>Session: {session_id}</p>
          <p>Name: {name}<br/>Email: {email}</p>
          <a id="approve" href="{approve_link}" style='display:inline-block;margin-top:12px;padding:10px 16px;background:#0ea5a3;color:white;border-radius:6px;text-decoration:none'>Approve & Return</a>
        </div>
      </body>
    </html>
    """
    return HTMLResponse(content=html)


@router.get("/mono-callback")
async def mono_callback(request: Request):
    # This endpoint simulates the redirect from Mono back to the app.
    # In a real flow, Mono would redirect to a frontend URL; for dev we redirect to the frontend callback page.
    query = request.query_params
    code = query.get("code")
    name = query.get("name", "Demo")
    email = query.get("email", "demo@trustlayer.demo")
    # Redirect to frontend callback that will POST to /mono/exchange-token
    frontend_base = os.getenv("FRONTEND_BASE_URL", "http://127.0.0.1:5173")
    frontend_url = f"{frontend_base}/mono-callback?code={code}&name={urllib.parse.quote(name)}&email={urllib.parse.quote(email)}"
    return RedirectResponse(url=frontend_url)


@router.post("/webhook/mono")
async def mono_webhook(request: Request, db: Session = Depends(get_db)):
    raw = await request.body()
    signature = request.headers.get("x-mono-signature", "")
    if not verify_webhook_signature(raw, signature):
        return {"status": "ignored"}

    payload = await request.json()
    # handle account_connected event
    event = payload.get("event") or payload.get("type")
    if event == "account.connected" or event == "account_connected":
        account_id = payload.get("data", {}).get("account_id")
        user_email = payload.get("data", {}).get("email")
        if account_id and user_email:
            user = db.query(User).filter(User.email == user_email).first()
            if user:
                user.mono_account_id = account_id
                db.add(user)
                db.commit()
    return {"status": "ok"}
