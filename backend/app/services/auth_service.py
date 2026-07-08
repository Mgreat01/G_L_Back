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


class AuthService:

    @staticmethod
    def register(
        db: Session,
        payload: RegisterSchema
    ):

        try:

            allowed_roles = [
                "user",
                "rescuer"
            ]

            role = (
                payload.role
                if payload.role in allowed_roles
                else "user"
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
                public_key=payload.public_key
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
                    "role": user.role
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
                    User.hashed_password
                )
            )\
            .filter(User.email == payload.email)\
            .first()

        if not user:

            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
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
                "role": user.role
            }
        }
