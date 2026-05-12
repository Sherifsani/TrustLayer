import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from jose import jwt

load_dotenv()

from api.models.schemas import LoginRequest, LoginResponse

# Local DB lookup so demo login tokens use the actual user UUID stored in the database
from db.session import SessionLocal, get_user

router = APIRouter()

SECRET_KEY = os.getenv("SECRET_KEY", "")
ALGORITHM = "HS256"

# Demo credentials map to seeded user handles (user_handle) — we resolve to UUID at login
DEMO_USERS = {
    "adaeze@trustlayer.demo": {"password": "demo1234", "user_id": "usr_adaeze001"},
    "emeka@trustlayer.demo":  {"password": "demo1234", "user_id": "usr_emeka001"},
}


@router.post("/auth/login", response_model=LoginResponse)
async def login(payload: LoginRequest):
    user_data = DEMO_USERS.get(payload.email)
    if not user_data or user_data["password"] != payload.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Resolve the demo user handle to the actual UUID (if present in DB).
    db = SessionLocal()
    try:
        user = get_user(db, user_data["user_id"])  # handles both UUID and handle lookup
        sub_value = str(user.id) if user else user_data["user_id"]
    finally:
        db.close()

    expire = datetime.utcnow() + timedelta(hours=24)
    token = jwt.encode(
        {"sub": sub_value, "exp": expire},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user_id=sub_value,
    )
