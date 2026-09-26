from enum import StrEnum


class AlertStatus(StrEnum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    ASSIGNED = "assigned"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


_ALLOWED_TRANSITIONS = {
    AlertStatus.ACTIVE: frozenset({AlertStatus.ACKNOWLEDGED, AlertStatus.ASSIGNED, AlertStatus.CANCELLED}),
    AlertStatus.ACKNOWLEDGED: frozenset({AlertStatus.ASSIGNED, AlertStatus.CANCELLED}),
    AlertStatus.ASSIGNED: frozenset({AlertStatus.ACKNOWLEDGED, AlertStatus.RESOLVED}),
    AlertStatus.RESOLVED: frozenset(),
    AlertStatus.CANCELLED: frozenset(),
}


def can_transition(current: str, target: str) -> bool:
    try:
        return AlertStatus(target) in _ALLOWED_TRANSITIONS[AlertStatus(current)]
    except ValueError:
        return False

