from sqlalchemy.orm import Session

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

        existing_email = db.query(User)\
            .filter(User.email == payload.email)\
            .first()

        if existing_email:
            raise HTTPException(
                status_code=400,
                detail="Email already exists"
            )

        existing_username = db.query(User)\
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
            role=payload.role,
            public_key=payload.public_key
        )

        db.add(user)

        db.commit()

        db.refresh(user)

        token = create_access_token(user.id)

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role
            }
        }

    @staticmethod
    def login(
        db: Session,
        payload: LoginSchema
    ):

        user = db.query(User)\
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

        token = create_access_token(user.id)

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role
            }
        }