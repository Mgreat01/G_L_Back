from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.location_schema import LocationCreate
from app.services.location_service import LocationService

router = APIRouter(
    prefix="/locations",
    tags=["Locations"]
)

@router.post("/")
def create_location(
    location: LocationCreate,
    db: Session = Depends(get_db)
):
    return LocationService.create_location(db, location)

@router.get("/{alert_id}")
def get_locations(
    alert_id: str,
    db: Session = Depends(get_db)
):
    return LocationService.get_locations(db, alert_id)