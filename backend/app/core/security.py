from datetime import datetime, timedelta
from pathlib import Path

from jose import jwt, JWTError

from passlib.context import CryptContext

from app.models.user_model import User
from app.core.database import SessionLocal
from sqlalchemy.orm import load_only

from fastapi import (
    Depends,
    HTTPException,
    status
)

from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials
)

from dotenv import load_dotenv

import os


backend_dir = Path(__file__).resolve().parents[2]
project_root = backend_dir.parent

load_dotenv(project_root / ".env")
load_dotenv(backend_dir / ".env", override=True)

SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY must be configured")

ALGORITHM = os.getenv("ALGORITHM", "HS256")

ACCESS_TOKEN_EXPIRE_HOURS = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_HOURS", 24)
)


security = HTTPBearer()

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def hash_password(password: str):

    return pwd_context.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str
):

    return pwd_context.verify(
        plain_password,
        hashed_password
    )


def create_access_token(user):

    expire = datetime.utcnow() + timedelta(
        hours=ACCESS_TOKEN_EXPIRE_HOURS
    )

    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "exp": expire
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def get_user_from_token(token: str, db):
    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("sub")

        if not user_id:

            return None

        user = db.query(User)\
            .options(
                load_only(
                    User.id,
                    User.email,
                    User.role,
                    User.username,
                    User.is_active,
                    User.email_verified
                )
            )\
            .filter(User.id == user_id)\
            .first()

        if not user:

            return None

        if not user.is_active:
            return None

        return {
            "id": str(user.id),
            "email": user.email,
            "role": user.role,
            "username": user.username,
            "is_active": user.is_active,
            "email_verified": user.email_verified
        }

    except JWTError:

        return None


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):

    token = credentials.credentials

    db = SessionLocal()

    try:
        current_user = get_user_from_token(token, db)

        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )

        return current_user

    finally:
        db.close()



def require_roles(allowed_roles: list):

    def role_checker(
        current_user=Depends(get_current_user)
    ):

        if current_user["role"] not in allowed_roles:

            raise HTTPException(
                status_code=403,
                detail="Access denied"
            )

        return current_user

    return role_checker
