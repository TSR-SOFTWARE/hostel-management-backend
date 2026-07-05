from datetime import datetime, timezone
from typing import Optional


def hostel_document(
    owner_id: str,
    name: str,
    address: str,
    city: str,
    state: str,
    pincode: str,
    phone: Optional[str],
    email: Optional[str],
    total_rooms: int,
    created_by: str,
) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "owner_id": owner_id,
        "name": name,
        "address": address,
        "city": city,
        "state": state,
        "pincode": pincode,
        "phone": phone,
        "email": email,
        "total_rooms": total_rooms,
        "is_active": True,
        "created_at": now,
        "created_by": created_by,
        "updated_at": now,
        "updated_by": created_by,
        "deleted_at": None,
    }
