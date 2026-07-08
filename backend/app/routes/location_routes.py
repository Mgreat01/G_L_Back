from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.location_schema import LocationCreate, RescueTeamLocationCreate
from app.services.location_service import LocationService

from app.core.security import get_current_user

router = APIRouter(
    prefix="/locations",
    tags=["Locations"]
)

@router.post("/")
def create_location(
    location: LocationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)

):


    return LocationService.create_location(
        db,
        location,
        current_user
    )

@router.get("/{alert_id}")
def get_locations(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return LocationService.get_locations(db, alert_id, current_user)


@router.post("/rescue-team")
def create_rescue_team_location(
    location: RescueTeamLocationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return LocationService.create_rescue_team_location(
        db,
        location,
        current_user
    )
