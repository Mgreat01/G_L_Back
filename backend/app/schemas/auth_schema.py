from typing import Literal

from pydantic import (
    BaseModel,
    EmailStr,
    Field
)

from typing import Optional, Literal

role: Optional[Literal[
    "user",
    "rescuer",
    "admin",
    "operator"
]] = "user"


class RegisterSchema(BaseModel):

    username: str = Field(
        min_length=3,
        max_length=50
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=72
    )

    role: Optional[
        Literal[
            "user",
            "rescuer",
            "admin"
        ]
    ] = "user"

    public_key: Optional[str] = None


class LoginSchema(BaseModel):

    email: EmailStr

    password: str


class TokenResponse(BaseModel):

    access_token: str

    token_type: str = "bearer"