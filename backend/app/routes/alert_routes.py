from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.database import get_db

from backend.app.schemas.alert_schema import (
    AlertCreate,
    AlertUpdate,
    AlertResponse
)

from backend.app.services.alert_service import AlertService

router = APIRouter(
    prefix="/alerts",
    tags=["Alerts"]
)

@router.post("", response_model=AlertResponse)
def create_alert(
    payload: AlertCreate,
    db: Session = Depends(get_db)
):

    user_id = "550e8400-e29b-41d4-a716-446655440000"

    return AlertService.create_alert(
        db,
        payload,
        user_id
    )

@router.get("", response_model=list[AlertResponse])
def get_alerts(
    db: Session = Depends(get_db)
):

    return AlertService.get_alerts(db)

@router.put("/{alert_id}")
def update_alert(
    alert_id: str,
    payload: AlertUpdate,
    db: Session = Depends(get_db)
):

    alert = AlertService.update_alert(
        db,
        alert_id,
        payload
    )

    if not alert:
        raise HTTPException(
            status_code=404,
            detail="Alert not found"
        )

    return alert