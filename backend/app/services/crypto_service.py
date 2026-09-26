from fastapi import HTTPException, status
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from app.domain.users.roles import is_privileged_role, is_rescue_role, normalize_role


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
