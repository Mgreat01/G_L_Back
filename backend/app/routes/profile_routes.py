from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)

from sqlalchemy.orm import Session

from app.core.database import get_db

from app.services.profile_service import ProfileService
from app.schemas.profile_schema import ProfileUpdate

from app.core.security import (
    get_current_user,
    require_roles
)

router = APIRouter(
    prefix="/profiles",
    tags=["Profiles"]
)



@router.get("/me")
def my_profile(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    return ProfileService.get_profile(
        db,
        current_user["id"]
    )



@router.put("/me")
def update_my_profile(
    data: ProfileUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    return ProfileService.update_profile(
        db,
        current_user["id"],
        data.dict(exclude_unset=True)
    )



@router.get("/rescue-team/public-keys")
def rescue_public_keys(
    current_user = Depends(
        require_roles([
            "rescuer",
            "rescue_team",
            "admin"
        ])
    ),
    db: Session = Depends(get_db)
):

    return ProfileService.get_rescue_keys(db)
