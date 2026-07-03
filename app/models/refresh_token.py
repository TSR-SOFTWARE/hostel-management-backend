from datetime import datetime, timezone
from typing import Optional


def refresh_token_document(
    user_id: str,
    token_hash: str,
    expiry: datetime,
    ip_address: Optional[str] = None,
    device_info: Optional[str] = None,
) -> dict:
    return {
        "user_id": user_id,
        "token_hash": token_hash,
        "expiry_date": expiry,
        "created_at": datetime.now(timezone.utc),
        "revoked_at": None,
        "ip_address": ip_address,
        "device_info": device_info,
    }
