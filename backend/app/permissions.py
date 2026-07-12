ROLES_PERMISSIONS = {
    "user": [
        "profile:read",
        "profile:write"
    ],
    "rescuer": [
        "profile:read",
        "profile:write",
        "rescue:create",
        "rescue:update"
    ],
    "admin": [
        "profile:read",
        "profile:write",
        "rescue:create",
        "rescue:update",
        "rescue:delete",
        "users:manage"
    ]
}
