from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_db
from api.models.db_models import User
from api.models.schemas import UserProfileResponse
from db.session import get_user

router = APIRouter()


@router.get("/user/{user_id}", response_model=UserProfileResponse)
async def get_user_profile(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if str(user.id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    return UserProfileResponse(
        user_id=user.user_handle or str(user.id),
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        phone=user.phone,
        location=user.location,
        kyc_status=user.kyc_status,
        identity_confidence=user.identity_confidence,
        joined=user.created_at,
        # BVN/NIN are SHA-256 hashed at ingestion — real digits unrecoverable
        nin_masked="•••• •••• ****",
        bvn_masked="•••• •••• ****",
    )
