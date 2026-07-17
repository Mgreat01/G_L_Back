from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from app.core.database import get_db

from app.core.security import (
    get_current_user,
    require_roles
)

from app.schemas.auth_schema import (
    RegisterSchema,
    LoginSchema
)

from app.services.auth_service import AuthService

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



@router.get("/me")
def me(
    current_user: dict = Depends(get_current_user)
):

    return current_user


@router.put("/users/{user_id}/activation")
def set_account_active(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles(["admin"]))
):
    return AuthService.set_account_active(db, user_id)


@router.put("/users/{user_id}/verify-email")
def verify_email(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles(["admin"]))
):
    return AuthService.verify_email(db, user_id)


@router.get("/users/role/{role}")
def get_users_by_role(
    role: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles(["admin"]))
):
    return AuthService.get_users_by_role(db, role)


@router.get("/users")
def get_all_users(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles(["admin"]))
):
    return AuthService.get_all_users(db)


@router.put("/users/{user_id}/rescuer-status")
def set_rescuer_status(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles(["admin"]))
):
    return AuthService.set_rescuer_status(db, user_id)
