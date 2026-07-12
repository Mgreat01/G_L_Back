from sqlalchemy.orm import Session
from sqlalchemy.orm import load_only
from sqlalchemy.exc import SQLAlchemyError

from fastapi import HTTPException

from app.models.user_model import User

from app.schemas.auth_schema import (
    RegisterSchema,
    LoginSchema
)

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token
)
from app.services.crypto_service import normalize_role, validate_public_key


class AuthService:

    @staticmethod
    def register(
        db: Session,
        payload: RegisterSchema
    ):

        try:

            allowed_roles = [
                "user",
                "rescuer",
                "rescue_team"
            ]

            role = normalize_role(
                payload.role
                if payload.role in allowed_roles
                else "user"
            )

            validate_public_key(
                payload.public_key,
                payload.public_key_algorithm
            )

            existing_email = db.query(User)\
                .options(load_only(User.id))\
                .filter(User.email == payload.email)\
                .first()

            if existing_email:

                raise HTTPException(
                    status_code=400,
                    detail="Email already exists"
                )

            existing_username = db.query(User)\
                .options(load_only(User.id))\
                .filter(User.username == payload.username)\
                .first()

            if existing_username:

                raise HTTPException(
                    status_code=400,
                    detail="Username already exists"
                )

            user = User(
                username=payload.username,
                email=payload.email,
                hashed_password=hash_password(
                    payload.password
                ),
                role=role,
                public_key=payload.public_key,
                public_key_algorithm=payload.public_key_algorithm,
                is_active=True,
                email_verified=False
            )

            db.add(user)

            db.commit()

            db.refresh(user)

            token = create_access_token(user)

            return {
                "access_token": token,
                "token_type": "bearer",
                "user": {
                    "id": str(user.id),
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
                    "is_active": user.is_active,
                    "email_verified": user.email_verified
                }
            }

        except SQLAlchemyError as e:

            db.rollback()

            raise HTTPException(
                status_code=500,
                detail=f"Database error: {str(e)}"
            )

    @staticmethod
    def login(
        db: Session,
        payload: LoginSchema
    ):

        user = db.query(User)\
            .options(
                load_only(
                    User.id,
                    User.username,
                    User.email,
                    User.role,
                    User.hashed_password,
                    User.is_active,
                    User.email_verified
                )
            )\
            .filter(User.email == payload.email)\
            .first()

        if not user:

            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=403,
                detail="Account is disabled"
            )

        valid_password = verify_password(
            payload.password,
            user.hashed_password
        )

        if not valid_password:

            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )

        token = create_access_token(user)

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
                    "is_active": user.is_active,
                    "email_verified": user.email_verified
                }
            }

    @staticmethod
    def set_account_active(db: Session, user_id: str, is_active: bool):
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.is_active = is_active
        db.commit()
        db.refresh(user)

        return {
            "id": str(user.id),
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "email_verified": user.email_verified
        }

    @staticmethod
    def verify_email(db: Session, user_id: str):
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.email_verified = True
        db.commit()
        db.refresh(user)

        return {
            "id": str(user.id),
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "email_verified": user.email_verified
        }

    @staticmethod
    def get_users_by_role(db: Session, role: str):
        users = db.query(User)\
            .filter(User.role == role)\
            .all()

        return [
            {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active,
                "email_verified": user.email_verified,
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
            for user in users
        ]

    @staticmethod
    def get_all_users(db: Session):
        users = db.query(User).all()

        return [
            {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active,
                "email_verified": user.email_verified,
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
            for user in users
        ]
