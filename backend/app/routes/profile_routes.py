from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.profile_service import ProfileService

router = APIRouter(
    prefix="/profiles",
    tags=["Profiles"]
)

@router.get("/{user_id}")
def get_profile(
    user_id: str,
    db: Session = Depends(get_db)
):
    return ProfileService.get_profile(db, user_id)

@router.put("/{user_id}")
def update_profile(
    user_id: str,
    db: Session = Depends(get_db)
):
    return ProfileService.update_profile(db, user_id)

@router.get("/rescue-team/public-keys")
def rescue_public_keys(
    db: Session = Depends(get_db)
):
    return ProfileService.get_rescue_keys(db)