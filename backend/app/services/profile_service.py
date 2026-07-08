from sqlalchemy.orm import Session
from sqlalchemy.orm import load_only
from fastapi import HTTPException

from app.models.user_model import User
from app.services.crypto_service import validate_public_key


class ProfileService:

    @staticmethod
    def get_profile(
        db: Session,
        user_id: str
    ):

        user = db.query(User)\
            .options(
                load_only(
                    User.id,
                    User.username,
                    User.email,
                    User.role,
                    User.public_key,
                    User.public_key_algorithm,
                    User.is_active,
                    User.email_verified
                )
            )\
            .filter(User.id == user_id)\
            .first()

        if not user:
            return None

        return {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "public_key": user.public_key,
            "public_key_algorithm": user.public_key_algorithm,
            "is_active": user.is_active,
            "email_verified": user.email_verified
        }

    @staticmethod
    def update_profile(
        db: Session,
        user_id: str,
        data: dict
    ):

        user = db.query(User)\
            .options(
                load_only(
                    User.id,
                    User.username,
                    User.email,
                    User.role,
                    User.public_key,
                    User.public_key_algorithm
                )
            )\
            .filter(User.id == user_id)\
            .first()

        if not user:
            return None

        if data.get("public_key"):
            validate_public_key(
                data.get("public_key"),
                data.get("public_key_algorithm") or user.public_key_algorithm
            )

        if "email" in data:
            existing_email = db.query(User).filter(
                User.email == data["email"],
                User.id != user_id
            ).first()

            if existing_email:
                raise HTTPException(status_code=400, detail="Email already exists")

        if "username" in data:
            existing_username = db.query(User).filter(
                User.username == data["username"],
                User.id != user_id
            ).first()

            if existing_username:
                raise HTTPException(status_code=400, detail="Username already exists")

        forbidden_fields = [
            "id",
            "role",
            "hashed_password"
        ]

        for field in forbidden_fields:

            if field in data:
                del data[field]

        for key, value in data.items():

            setattr(user, key, value)

        db.commit()

        db.refresh(user)

        return {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "public_key": user.public_key,
            "public_key_algorithm": user.public_key_algorithm
        }

    @staticmethod
    def get_rescue_keys(db: Session):
        users = db.query(User)\
            .options(
                load_only(
                    User.id,
                    User.username,
                    User.role,
                    User.public_key,
                    User.public_key_algorithm
                )
            )\
            .filter(
                User.role.in_(["rescuer", "rescue_team"]),
                User.is_active.is_(True),
                User.public_key.isnot(None)
            )\
            .all()

        return [
            {
                "id": str(user.id),
                "username": user.username,
                "role": user.role,
                "public_key": user.public_key,
                "public_key_algorithm": user.public_key_algorithm
            }
            for user in users
        ]
