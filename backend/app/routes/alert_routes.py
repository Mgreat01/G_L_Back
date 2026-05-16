from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.alert_schema import (
    AlertCreate,
    AlertUpdate,
    AlertResponse
)
from app.services.alert_service import AlertService

router = APIRouter(
    prefix="/alerts",
    tags=["Alerts"]
)

@router.post("/", response_model=AlertResponse)
def create_alert(alert: AlertCreate, db: Session = Depends(get_db)):
    return AlertService.create_alert(db, alert)

@router.get("/", response_model=list[AlertResponse])
def get_alerts(db: Session = Depends(get_db)):
    return AlertService.get_alerts(db)

@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(alert_id: str, db: Session = Depends(get_db)):
    return AlertService.get_alert(db, alert_id)

@router.put("/{alert_id}", response_model=AlertResponse)
def update_alert(
    alert_id: str,
    update: AlertUpdate,
    db: Session = Depends(get_db)
):
    return AlertService.update_alert(db, alert_id, update)

@router.get("/nearby/search")
def nearby_alerts(
    latitude: float,
    longitude: float,
    radius: float = 5000,
    db: Session = Depends(get_db)
):
    return AlertService.get_nearby_alerts(
        db,
        latitude,
        longitude,
        radius
    )