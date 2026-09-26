from app.domain.users.roles import is_privileged_role, is_rescue_role, normalize_role


def test_rescue_team_is_normalized_to_rescuer():
    assert normalize_role("rescue_team") == "rescuer"
    assert is_rescue_role("rescue_team")


def test_only_operations_roles_are_privileged():
    assert is_privileged_role("admin")
    assert is_privileged_role("operator")
    assert not is_privileged_role("rescuer")

