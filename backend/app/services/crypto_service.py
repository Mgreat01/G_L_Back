from fastapi import HTTPException, status
from cryptography.hazmat.primitives.serialization import load_pem_public_key


ROLE_RESCUE_ALIASES = {"rescuer", "rescue_team"}
PRIVILEGED_ROLES = {"admin", "operator"}


def normalize_role(role: str | None) -> str:
    if role == "rescue_team":
        return "rescuer"
    return role or "user"


def is_rescue_role(role: str | None) -> bool:
    return normalize_role(role) in ROLE_RESCUE_ALIASES


def is_privileged_role(role: str | None) -> bool:
    return normalize_role(role) in PRIVILEGED_ROLES


def validate_public_key(public_key: str | None, algorithm: str | None = None):
    if not public_key:
        return

    try:
        load_pem_public_key(public_key.encode("utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid PEM public key"
        ) from exc
