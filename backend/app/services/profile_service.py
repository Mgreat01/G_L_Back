from sqlalchemy.orm import Session
from app.models.user_model import User


class ProfileService:

    @staticmethod
    def get_profile(db: Session, user_id: str):
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def update_profile(db: Session, user_id: str, data: dict):
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            return None

        for key, value in data.items():
            setattr(user, key, value)

        db.commit()
        db.refresh(user)

        return user