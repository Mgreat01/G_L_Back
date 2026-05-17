from sqlalchemy.orm import Session

from app.models.user_model import User


class ProfileService:

    @staticmethod
    def get_profile(
        db: Session,
        user_id: str
    ):

        user = db.query(User)\
            .filter(User.id == user_id)\
            .first()

        if not user:
            return None

        return {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "public_key": user.public_key
        }

    @staticmethod
    def update_profile(
        db: Session,
        user_id: str,
        data: dict
    ):

        user = db.query(User)\
            .filter(User.id == user_id)\
            .first()

        if not user:
            return None

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
            "public_key": user.public_key
        }