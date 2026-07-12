# app/api/dependencies.py
from typing import List

from app.core.security import get_current_user
from app.models.user_model import User
from app.permissions import ROLES_PERMISSIONS
from fastapi import Depends, HTTPException
from starlette import status


class PermissionChecker:
    def __init__(self, required_permissions: List[str]):
        self.required_permissions = required_permissions

    def __call__(self, current_user: User = Depends(get_current_user)):
        user_permissions = ROLES_PERMISSIONS.get(current_user.role, [])

        for permission in self.required_permissions:
            if permission not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have the necessary permissions to perform this action."
                )

        return current_user
