import random
import string
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from app.core.config import settings
from app.repositories.otp_repository import OtpRepository
from app.repositories.user_repository import UserRepository
from app.models.otp_request import otp_document, OtpPurpose


def _generate_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


def _send_email(to: str, otp: str, purpose: str):
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        print(f"[DEV] OTP for {to}: {otp}")
        return
    subject = "Your OTP Code"
    body = f"Your OTP for {purpose.replace('_', ' ')} is: {otp}\n\nThis OTP expires in {settings.OTP_EXPIRE_MINUTES} minutes."
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_FROM or settings.SMTP_USER
    msg["To"] = to
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(msg["From"], [to], msg.as_string())
    except smtplib.SMTPException as e:
        print(f"[EMAIL ERROR] Failed to send OTP email to {to}: {e}")
        print(f"[DEV] OTP for {to}: {otp}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send OTP email. Please try again later.",
        )


class OtpService:
    def __init__(self, db):
        self.otp_repo = OtpRepository(db)
        self.user_repo = UserRepository(db)

    async def send_otp(self, identifier: str, purpose: OtpPurpose) -> str:
        user = await self.user_repo.find_by_identifier(identifier)
        if not user:
            # Don't reveal if user exists
            return "If the account exists, an OTP has been sent"

        otp = _generate_otp()
        expiry = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
        await self.otp_repo.insert(otp_document(user["id"], otp, purpose, expiry))

        # Send OTP via email if configured, otherwise print to console
        if user.get("email"):
            _send_email(user["email"], otp, purpose)
        else:
            print(f"[DEV] OTP for {identifier}: {otp}")
        return "If the account exists, an OTP has been sent"

    async def verify_otp(self, identifier: str, otp_code: str, purpose: str, mark_used: bool = True) -> str:
        user = await self.user_repo.find_by_identifier(identifier)
        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP")

        record = await self.otp_repo.find_latest(user["id"], purpose)
        if not record:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP")

        if record["attempts"] >= settings.MAX_OTP_ATTEMPTS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Maximum OTP attempts exceeded")

        await self.otp_repo.increment_attempts(record["id"])

        expiry = record["expiry_time"]
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)

        if datetime.now(timezone.utc) > expiry:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP has expired")

        if record["otp"] != otp_code:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP")

        if mark_used:
            await self.otp_repo.mark_used(record["id"])
        return user["id"]
