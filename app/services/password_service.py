from fastapi import HTTPException, status, Request
from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.repositories.user_repository import UserRepository
from app.repositories.password_history_repository import PasswordHistoryRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.models.password_history import password_history_document
from app.models.audit_log import audit_log_document


class PasswordService:
    def __init__(self, db):
        self.user_repo = UserRepository(db)
        self.history_repo = PasswordHistoryRepository(db)
        self.token_repo = RefreshTokenRepository(db)
        self.audit_repo = AuditLogRepository(db)

    async def _check_history(self, user_id: str, new_password: str):
        recent = await self.history_repo.get_recent(user_id, settings.PASSWORD_HISTORY_COUNT)
        for entry in recent:
            if verify_password(new_password, entry["password_hash"]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot reuse last {settings.PASSWORD_HISTORY_COUNT} passwords",
                )

    async def reset_password(self, user_id: str, new_password: str, request: Request):
        user = await self.user_repo.find_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        await self._check_history(user_id, new_password)

        new_hash = hash_password(new_password)
        await self.user_repo.update_password(user_id, new_hash)
        await self.history_repo.insert(password_history_document(user_id, new_hash))
        await self.token_repo.revoke_all_for_user(user_id)

        ip = request.client.host if request.client else None
        await self.audit_repo.insert(audit_log_document(user_id, "password_reset", "auth", ip_address=ip))

    async def change_password(self, user_id: str, old_password: str, new_password: str, request: Request):
        user = await self.user_repo.find_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if not verify_password(old_password, user["password_hash"]):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Old password is incorrect")

        await self._check_history(user_id, new_password)

        new_hash = hash_password(new_password)
        await self.user_repo.update_password(user_id, new_hash)
        await self.history_repo.insert(password_history_document(user_id, new_hash))
        await self.token_repo.revoke_all_for_user(user_id)

        ip = request.client.host if request.client else None
        await self.audit_repo.insert(audit_log_document(user_id, "password_changed", "auth", ip_address=ip))
