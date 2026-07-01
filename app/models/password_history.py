from datetime import datetime, timezone


def password_history_document(user_id: str, password_hash: str) -> dict:
    return {
        "user_id": user_id,
        "password_hash": password_hash,
        "created_at": datetime.now(timezone.utc),
    }
