from datetime import datetime, timezone
from typing import Optional


def audit_log_document(
    user_id: Optional[str],
    action: str,
    module: str,
    ip_address: Optional[str] = None,
    device: Optional[str] = None,
    browser: Optional[str] = None,
    meta: Optional[dict] = None,
) -> dict:
    return {
        "user_id": user_id,
        "action": action,
        "module": module,
        "ip_address": ip_address,
        "device": device,
        "browser": browser,
        "meta": meta or {},
        "created_at": datetime.now(timezone.utc),
    }
