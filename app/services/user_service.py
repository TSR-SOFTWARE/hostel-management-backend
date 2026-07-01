from fastapi import HTTPException, status
from app.core.security import hash_password
from app.repositories.user_repository import UserRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.password_history_repository import PasswordHistoryRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.models.user import user_document
from app.models.password_history import password_history_document
from app.models.audit_log import audit_log_document


class UserService:
    def __init__(self, db):
        self.db = db
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)
        self.history_repo = PasswordHistoryRepository(db)
        self.audit_repo = AuditLogRepository(db)
        self.token_repo = RefreshTokenRepository(db)

    async def create_user(self, data: dict, created_by: str, ip: str = None) -> dict:
        if not data.get("email") and not data.get("mobile"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email or mobile is required")

        if data.get("email"):
            existing = await self.user_repo.find_by_email(data["email"])
            if existing:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

        if data.get("mobile"):
            existing = await self.user_repo.find_by_mobile(data["mobile"])
            if existing:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Mobile already registered")

        role = await self.role_repo.find_by_id(data["role_id"])
        if not role:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role_id")

        pwd_hash = hash_password(data["password"])
        doc = user_document(
            owner_id=data.get("owner_id"),
            employee_id=data.get("employee_id"),
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=data.get("email"),
            mobile=data.get("mobile"),
            password_hash=pwd_hash,
            role_id=data["role_id"],
            created_by=created_by,
        )
        doc["status"] = "active"

        user_id = await self.user_repo.insert(doc)
        await self.history_repo.insert(password_history_document(user_id, pwd_hash))
        await self.audit_repo.insert(audit_log_document(created_by, "user_created", "user", ip_address=ip, meta={"new_user_id": user_id}))

        return await self.user_repo.find_by_id(user_id)

    async def get_user(self, user_id: str) -> dict:
        user = await self.user_repo.find_by_id(user_id)
        if not user or user.get("deleted_at"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        user.pop("password_hash", None)
        return user

    async def list_users(self, owner_id: str = None, page: int = 1, limit: int = 50) -> dict:
        skip = (page - 1) * limit
        users = await self.user_repo.list_users(owner_id=owner_id, skip=skip, limit=limit)
        total = await self.user_repo.count_users(owner_id=owner_id)
        for u in users:
            u.pop("password_hash", None)
        return {"total": total, "page": page, "limit": limit, "users": users}

    async def update_user(self, user_id: str, updates: dict, updated_by: str, ip: str = None) -> dict:
        user = await self.user_repo.find_by_id(user_id)
        if not user or user.get("deleted_at"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if updates.get("role_id"):
            role = await self.role_repo.find_by_id(updates["role_id"])
            if not role:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role_id")

        fields = {k: v for k, v in updates.items() if v is not None}
        if not fields:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

        await self.user_repo.update_fields(user_id, fields, updated_by)

        if "role_id" in fields:
            await self.audit_repo.insert(audit_log_document(updated_by, "role_changed", "user", ip_address=ip, meta={"target_user_id": user_id, "new_role": fields["role_id"]}))
        else:
            await self.audit_repo.insert(audit_log_document(updated_by, "user_updated", "user", ip_address=ip, meta={"target_user_id": user_id}))

        updated = await self.user_repo.find_by_id(user_id)
        updated.pop("password_hash", None)
        return updated

    async def delete_user(self, user_id: str, deleted_by: str, ip: str = None):
        if user_id == deleted_by:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own account")

        user = await self.user_repo.find_by_id(user_id)
        if not user or user.get("deleted_at"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        await self.user_repo.soft_delete(user_id, deleted_by)
        await self.token_repo.revoke_all_for_user(user_id)
        await self.audit_repo.insert(audit_log_document(deleted_by, "user_deleted", "user", ip_address=ip, meta={"target_user_id": user_id}))
