import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status, Request
from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.core.jwt import create_access_token, create_refresh_token, decode_token
from app.repositories.user_repository import UserRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.models.refresh_token import refresh_token_document
from app.models.audit_log import audit_log_document
from app.services.password_service import PasswordService


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _get_client_info(request: Request) -> dict:
    return {
        "ip": request.client.host if request.client else None,
        "device": request.headers.get("user-agent", ""),
    }


class AuthService:
    def __init__(self, db):
        self.db = db
        self.user_repo = UserRepository(db)
        self.token_repo = RefreshTokenRepository(db)
        self.audit_repo = AuditLogRepository(db)

    async def login(self, identifier: str, password: str, request: Request) -> dict:
        client = _get_client_info(request)
        user = await self.user_repo.find_by_identifier(identifier)

        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

        # Auto-unlock if lock period expired
        user = await self.user_repo.unlock_if_expired(user)

        if user["status"] == "deleted":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
        if user["status"] == "inactive":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")
        if user["is_locked"] or user["status"] == "locked":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is locked. Try again later")

        if not verify_password(password, user["password_hash"]):
            failed = user["failed_attempts"] + 1
            lock = failed >= settings.MAX_FAILED_LOGIN_ATTEMPTS
            locked_until = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCOUNT_LOCK_MINUTES) if lock else None
            await self.user_repo.increment_failed_attempts(user["id"], lock=lock, locked_until=locked_until)
            await self.audit_repo.insert(audit_log_document(user["id"], "failed_login", "auth", **client))
            if lock:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account locked due to too many failed attempts")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

        await self.user_repo.update_login_success(user["id"])

        access_token = create_access_token({"sub": user["id"], "role": user["role_id"]})
        raw_refresh = secrets.token_urlsafe(64)
        refresh_token_hash = _hash_token(raw_refresh)

        expiry = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self.token_repo.insert(
            refresh_token_document(user["id"], refresh_token_hash, expiry, client["ip"], client["device"])
        )
        await self.audit_repo.insert(audit_log_document(user["id"], "login", "auth", **client))

        return {"access_token": access_token, "refresh_token": raw_refresh, "token_type": "bearer"}

    async def logout(self, refresh_token: str, user_id: str, request: Request):
        client = _get_client_info(request)
        await self.token_repo.revoke(_hash_token(refresh_token))
        await self.audit_repo.insert(audit_log_document(user_id, "logout", "auth", **client))

    async def refresh_access_token(self, raw_refresh_token: str) -> dict:
        token_hash = _hash_token(raw_refresh_token)
        stored = await self.token_repo.find_active(token_hash)
        if not stored:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or revoked refresh token")

        expiry = stored["expiry_date"]
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expiry:
            await self.token_repo.revoke(token_hash)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

        user = await self.user_repo.find_by_id(stored["user_id"])
        if not user or user["status"] != "active":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

        # Rotate refresh token
        await self.token_repo.revoke(token_hash)
        new_access = create_access_token({"sub": user["id"], "role": user["role_id"]})
        new_raw_refresh = secrets.token_urlsafe(64)
        new_expiry = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self.token_repo.insert(
            refresh_token_document(user["id"], _hash_token(new_raw_refresh), new_expiry)
        )
        return {"access_token": new_access, "refresh_token": new_raw_refresh, "token_type": "bearer"}
