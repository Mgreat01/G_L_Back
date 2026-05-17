from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from app.core.database import get_db

from app.core.security import get_current_user

from app.schemas.auth_schema import (
    RegisterSchema,
    LoginSchema
)

from app.services.auth_service import AuthService

from app.core.security import require_roles

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)



@router.post("/register")
def register(
    payload: RegisterSchema,
    db: Session = Depends(get_db)
):

    return AuthService.register(
        db,
        payload
    )



@router.post("/login")
def login(
    payload: LoginSchema,
    db: Session = Depends(get_db)
):

    return AuthService.login(
        db,
        payload
    )



@router.get("/secure-test")
def secure_test(
    current_user: dict = Depends(get_current_user)
):

    return {
        "message": "secure route",
        "user_id": current_user["id"]
    }

@router.get("/me")
def me(
    current_user: dict = Depends(get_current_user)
):

    return current_user

@router.get("/admin-only")
def admin_route(
    current_user = Depends(
        require_roles(["admin"])
    )
):

    return {
        "message": "admin access"
    }

@router.get("/rescuer-only")
def rescuer_route(
    current_user = Depends(
        require_roles([
            "rescuer",
            "admin"
        ])
    )
):

    return {
        "message": "rescuer access"
    }