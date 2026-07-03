from datetime import datetime, timezone
from enum import Enum


class OtpPurpose(str, Enum):
    forgot_password = "forgot_password"
    email_verification = "email_verification"
    mobile_verification = "mobile_verification"


def otp_document(user_id: str, otp: str, purpose: OtpPurpose, expiry: datetime) -> dict:
    return {
        "user_id": user_id,
        "otp": otp,
        "purpose": purpose,
        "expiry_time": expiry,
        "attempts": 0,
        "is_used": False,
        "created_at": datetime.now(timezone.utc),
    }
