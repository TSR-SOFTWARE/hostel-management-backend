from datetime import datetime, timezone


def role_document(name: str, description: str, is_system_role: bool = False) -> dict:
    return {
        "role_name": name,
        "description": description,
        "is_system_role": is_system_role,
        "created_at": datetime.now(timezone.utc),
    }


def permission_document(module: str, action: str, description: str) -> dict:
    return {
        "module": module,
        "action": action,
        "description": description,
    }


def role_permission_document(role_id: str, permission_id: str) -> dict:
    return {
        "role_id": role_id,
        "permission_id": permission_id,
    }
