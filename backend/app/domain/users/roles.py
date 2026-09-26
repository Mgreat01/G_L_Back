from enum import StrEnum


class Role(StrEnum):
    USER = "user"
    RESCUER = "rescuer"
    RESCUE_TEAM = "rescue_team"
    ADMIN = "admin"
    OPERATOR = "operator"


ROLE_RESCUE_ALIASES = frozenset({Role.RESCUER, Role.RESCUE_TEAM})
PRIVILEGED_ROLES = frozenset({Role.ADMIN, Role.OPERATOR})


def normalize_role(role: str | None) -> str:
    """Return the canonical business role without depending on transport concerns."""
    return Role.RESCUER if role == Role.RESCUE_TEAM else (role or Role.USER)


def is_rescue_role(role: str | None) -> bool:
    return normalize_role(role) in ROLE_RESCUE_ALIASES


def is_privileged_role(role: str | None) -> bool:
    return normalize_role(role) in PRIVILEGED_ROLES

