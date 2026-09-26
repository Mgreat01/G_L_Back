from app.domain.alerts.rules import can_transition


def test_alert_follows_the_intervention_workflow():
    assert can_transition("active", "acknowledged")
    assert can_transition("active", "assigned")
    assert can_transition("assigned", "acknowledged")
    assert can_transition("acknowledged", "assigned")
    assert can_transition("assigned", "resolved")


def test_terminal_alert_cannot_be_reopened():
    assert not can_transition("resolved", "active")
    assert not can_transition("cancelled", "active")
