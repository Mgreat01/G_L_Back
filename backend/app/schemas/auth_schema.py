from pydantic import BaseModel, EmailStr
from typing import Optional


class RegisterSchema(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: Optional[str] = "user"
    public_key: Optional[str] = None


class LoginSchema(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"