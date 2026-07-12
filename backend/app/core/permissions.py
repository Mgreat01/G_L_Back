from app.services.crypto_service import normalize_role, is_privileged_role, is_rescue_role


def can_view_alert(current_user: dict, alert) -> bool:
    """
    Vérifie si l'utilisateur peut voir une alerte.
    
    Permissions:
    - admin/operator: peut voir toutes les alertes
    - user: peut voir ses propres alertes
    - rescuer/rescue_team: peut voir les alertes qui lui sont assignées
    """
    role = normalize_role(current_user["role"])
    user_id = current_user["id"]

    if role in ["admin", "operator"]:
        return True

    if str(alert.user_id) == user_id:
        return True

    if is_rescue_role(role) and str(alert.assigned_to) == user_id:
        return True

    return False


def can_update_alert(current_user: dict, alert, new_status: str = None, new_assigned_to: str = None) -> bool:
    """
    Vérifie si l'utilisateur peut modifier une alerte.
    
    Permissions:
    - admin/operator: peut modifier severity, status, assigned_to
    - user: peut seulement annuler ses propres alertes (status = cancelled)
    - rescuer/rescue_team: peut modifier le status des alertes qui lui sont assignées
      (acknowledged, assigned, resolved)
    """
    role = normalize_role(current_user["role"])
    user_id = current_user["id"]
    is_owner = str(alert.user_id) == user_id
    is_assigned = str(alert.assigned_to) == user_id

    if role in ["admin", "operator"]:
        return True

    if role == "user":
        if is_owner and new_status == "cancelled":
            return True
        return False

    if is_rescue_role(role):
        if is_assigned and new_status in ["acknowledged", "assigned", "resolved"]:
            return True
        return False

    return False


def can_assign_alert(current_user: dict) -> bool:
    """
    Vérifie si l'utilisateur peut assigner des alertes.
    
    Permissions:
    - admin/operator: peut assigner des alertes
    - user/rescuer/rescue_team: ne peut pas assigner
    """
    role = normalize_role(current_user["role"])
    return is_privileged_role(role)


def can_modify_severity(current_user: dict) -> bool:
    """
    Vérifie si l'utilisateur peut modifier la sévérité d'une alerte.
    
    Permissions:
    - admin/operator: peut modifier la sévérité
    - user/rescuer/rescue_team: ne peut pas modifier
    """
    role = normalize_role(current_user["role"])
    return is_privileged_role(role)


def can_view_all_alerts(current_user: dict) -> bool:
    """
    Vérifie si l'utilisateur peut voir toutes les alertes (pas seulement les siennes).
    
    Permissions:
    - admin/operator: peut voir toutes les alertes
    - user: voit seulement ses alertes
    - rescuer/rescue_team: voit les alertes assignées + nearby
    """
    role = normalize_role(current_user["role"])
    return role in ["admin", "operator"]


def can_view_nearby_alerts(current_user: dict) -> bool:
    """
    Vérifie si l'utilisateur peut voir les alertes nearby.
    
    Permissions:
    - admin/operator/rescuer/rescue_team: peut voir les alertes nearby
    - user: ne peut pas voir les alertes nearby
    """
    role = normalize_role(current_user["role"])
    return role in ["admin", "operator", "rescuer", "rescue_team"]
