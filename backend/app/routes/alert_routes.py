from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.alert_schema import (
    AlertCreate,
    AlertUpdate,
    AlertResponse
)
from app.services.alert_service import AlertService
from app.core.security import get_current_user

router = APIRouter(
    prefix="/alerts",
    tags=["Alerts"]
)


@router.post("/", response_model=AlertResponse)
def create_alert(
    alert: AlertCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    return AlertService.create_alert(
        db,
        alert,
        current_user["id"]
    )


@router.get("/")
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