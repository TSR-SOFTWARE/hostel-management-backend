from datetime import datetime, timezone
from typing import Optional
from enum import Enum


class UserStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    locked = "locked"
    deleted = "deleted"
    pending_verification = "pending_verification"


def user_document(
    owner_id: Optional[str],
    employee_id: Optional[str],
    first_name: str,
    last_name: str,
    email: Optional[str],
    mobile: Optional[str],
    password_hash: str,
    role_id: str,
    created_by: Optional[str] = None,
) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "owner_id": owner_id,
        "employee_id": employee_id,
        "first_name": first_name,
        "last_name": last_name,
        "email": email.lower() if email else None,
        "mobile": mobile,
        "password_hash": password_hash,
        "role_id": role_id,
        "status": UserStatus.pending_verification,
        "last_login": None,
        "failed_attempts": 0,
        "is_locked": False,
        "locked_until": None,
        "is_email_verified": False,
        "is_mobile_verified": False,
        "created_at": now,
        "created_by": created_by,
        "updated_at": now,
        "updated_by": created_by,
        "deleted_at": None,
    }
