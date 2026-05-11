import os
from typing import Generator

from dotenv import load_dotenv
from fastapi import Depends, Header, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

load_dotenv()

from api.models.db_models import User
from db.session import SessionLocal

VALID_BUSINESS_KEYS = {
    "biz_key_kwikloans_demo": "kwik_loans",
    "biz_key_fastcredit_demo": "fast_credit",
}

SECRET_KEY = os.getenv("SECRET_KEY", "")
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str | None = payload.get("sub")
        if not user_id:
            raise JWTError("missing sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    from db.session import get_user as _get_user
    user = _get_user(db, user_id)   # handles both UUID and user_handle (e.g. usr_adaeze001)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def get_business_api_key(authorization: str | None = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    key = authorization.removeprefix("Bearer ").strip()
    business_id = VALID_BUSINESS_KEYS.get(key)
    if not business_id:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return business_id
