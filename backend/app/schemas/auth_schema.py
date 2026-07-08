from pydantic import (
    BaseModel,
    EmailStr,
    Field
)

from typing import Optional, Literal

role: Optional[Literal[
    "user",
    "rescuer",
    "rescue_team",
    "admin",
    "operator"
]] = "user"


class RegisterSchema(BaseModel):

    username: str = Field(
        min_length=1,
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
            "rescue_team",
            "admin"
        ]
    ] = "user"

    public_key: Optional[str] = Field(default=None, max_length=20000)

    public_key_algorithm: Optional[
        Literal[
            "RSA-OAEP-SHA256",
            "ECDH-ES+A256KW"
        ]
    ] = "RSA-OAEP-SHA256"


class LoginSchema(BaseModel):

    email: EmailStr

    password: str


class TokenResponse(BaseModel):

    access_token: str

    token_type: str = "bearer"
