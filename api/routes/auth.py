import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from jose import jwt

load_dotenv()

from api.models.schemas import LoginRequest, LoginResponse

router = APIRouter()

SECRET_KEY = os.getenv("SECRET_KEY", "")
ALGORITHM = "HS256"

DEMO_USERS = {
    "adaeze@trustlayer.demo": {"password": "demo1234", "user_id": "usr_adaeze001"},
    "emeka@trustlayer.demo":  {"password": "demo1234", "user_id": "usr_emeka001"},
}


@router.post("/auth/login", response_model=LoginResponse)
async def login(payload: LoginRequest):
    user_data = DEMO_USERS.get(payload.email)
    if not user_data or user_data["password"] != payload.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    expire = datetime.utcnow() + timedelta(hours=24)
    token = jwt.encode(
        {"sub": user_data["user_id"], "exp": expire},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user_id=user_data["user_id"],
    )
