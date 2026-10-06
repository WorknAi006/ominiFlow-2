from sqlalchemy.orm import Session

from app.models import Permission, Role, RolePermission


SYSTEM_ROLES = [
    ("OWNER", "Tenant owner with full access."),
    ("ADMIN", "Tenant administrator."),
    ("MANAGER", "Manages teams and operational activities."),
    ("AGENT", "Handles assigned customer conversations and tasks."),
    ("VIEWER", "Read-only access to permitted tenant resources."),
    ("DEVELOPER", "Developer access for integrations and technical operations."),
]


SYSTEM_PERMISSIONS = [
    ("tenant:read", "View workspace details."),
    ("tenant:update", "Update workspace details."),
    ("user:read", "View team members."),
    ("user:create", "Invite team members."),
    ("user:update", "Change team member roles and status."),
    ("user:delete", "Remove team members."),
    ("channel:read", "View channel connections."),
    ("channel:create", "Create channel connections."),
    ("channel:update", "Update and disconnect channel connections."),
    ("channel:delete", "Delete channel connections."),
    ("contact:read", "View contacts."),
    ("contact:create", "Create contacts."),
    ("contact:update", "Update contacts."),
    ("conversation:read", "View conversations."),
    ("conversation:update", "Update conversations, status and read state."),
    ("conversation:assign", "Assign conversations to team members."),
    ("message:read", "View messages."),
    ("message:create", "Send messages."),
    ("template:read", "View message templates."),
    ("template:sync", "Synchronize message templates from providers."),
]


INBOX_READ_PERMISSIONS = [
    "contact:read",
    "conversation:read",
    "message:read",
    "template:read",
]

INBOX_AGENT_PERMISSIONS = [
    *INBOX_READ_PERMISSIONS,
    "contact:create",
    "contact:update",
    "conversation:update",
    "message:create",
]

INBOX_ALL_PERMISSIONS = [
    *INBOX_AGENT_PERMISSIONS,
    "conversation:assign",
    "template:sync",
]


# OWNER always receives every system permission (see seed_role_permissions).
ROLE_PERMISSIONS: dict[str, list[str]] = {
    "ADMIN": [
        "tenant:read",
        "tenant:update",
        "user:read",
        "user:create",
        "user:update",
        "user:delete",
        "channel:read",
        "channel:create",
        "channel:update",
        "channel:delete",
        *INBOX_ALL_PERMISSIONS,
    ],
    "MANAGER": [
        "tenant:read",
        "user:read",
        "user:create",
        "user:update",
        "channel:read",
        "channel:create",
        "channel:update",
        *INBOX_ALL_PERMISSIONS,
    ],
    "AGENT": ["tenant:read", "user:read", "channel:read", *INBOX_AGENT_PERMISSIONS],
    "VIEWER": ["tenant:read", "user:read", "channel:read", *INBOX_READ_PERMISSIONS],
    "DEVELOPER": ["tenant:read", "user:read", "channel:read", *INBOX_READ_PERMISSIONS],
}


def seed_system_roles(db: Session) -> None:
    for name, description in SYSTEM_ROLES:
        role = db.query(Role).filter(Role.name == name).first()

        if role is None:
            role = Role(
                name=name,
                description=description,
                is_system_role=True,
                is_active=True,
            )
            db.add(role)
        else:
            role.description = description
            role.is_system_role = True
            role.is_active = True

    db.commit()


def seed_permissions(db: Session) -> None:
    for name, description in SYSTEM_PERMISSIONS:
        permission = (
            db.query(Permission)
            .filter(Permission.name == name)
            .first()
        )

        if permission is None:
            permission = Permission(
                name=name,
                description=description,
                is_active=True,
            )
            db.add(permission)
        else:
            permission.description = description
            permission.is_active = True

    db.commit()


def seed_role_permissions(db: Session) -> None:
    permission_names = [name for name, _ in SYSTEM_PERMISSIONS]

    permissions = {
        permission.name: permission
        for permission in (
            db.query(Permission)
            .filter(Permission.name.in_(permission_names))
            .all()
        )
    }

    role_permissions = {
        **ROLE_PERMISSIONS,
        "OWNER": permission_names,
    }

    for role_name, role_permission_names in role_permissions.items():
        role = db.query(Role).filter(Role.name == role_name).first()

        if role is None:
            raise RuntimeError(
                f"Role {role_name} not found. Seed system roles first."
            )

        for permission_name in role_permission_names:
            permission = permissions[permission_name]

            exists = (
                db.query(RolePermission)
                .filter(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id == permission.id,
                )
                .first()
            )

            if exists is None:
                db.add(
                    RolePermission(
                        role_id=role.id,
                        permission_id=permission.id,
                    )
                )

    db.commit()
