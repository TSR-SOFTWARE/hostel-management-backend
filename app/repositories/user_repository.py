from datetime import datetime, timezone
from bson import ObjectId
from typing import Optional, List


class UserRepository:
    def __init__(self, db):
        self.col = db["users"]

    def _serialize(self, doc: dict) -> dict:
        if doc:
            doc["id"] = str(doc.pop("_id"))
        return doc

    async def find_by_id(self, user_id: str) -> Optional[dict]:
        doc = await self.col.find_one({"_id": ObjectId(user_id)})
        return self._serialize(doc) if doc else None

    async def find_by_email(self, email: str) -> Optional[dict]:
        doc = await self.col.find_one({"email": email.lower(), "deleted_at": None})
        return self._serialize(doc) if doc else None

    async def find_by_mobile(self, mobile: str) -> Optional[dict]:
        doc = await self.col.find_one({"mobile": mobile, "deleted_at": None})
        return self._serialize(doc) if doc else None

    async def find_by_identifier(self, identifier: str) -> Optional[dict]:
        user = await self.find_by_email(identifier)
        if not user:
            user = await self.find_by_mobile(identifier)
        return user

    async def insert(self, doc: dict) -> str:
        result = await self.col.insert_one(doc)
        return str(result.inserted_id)

    async def update_login_success(self, user_id: str):
        await self.col.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"last_login": datetime.now(timezone.utc), "failed_attempts": 0, "is_locked": False, "locked_until": None}},
        )

    async def increment_failed_attempts(self, user_id: str, lock: bool = False, locked_until: Optional[datetime] = None):
        update = {"$inc": {"failed_attempts": 1}}
        if lock:
            update["$set"] = {"is_locked": True, "locked_until": locked_until, "status": "locked"}
        await self.col.update_one({"_id": ObjectId(user_id)}, update)

    async def update_password(self, user_id: str, password_hash: str):
        await self.col.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"password_hash": password_hash, "updated_at": datetime.now(timezone.utc)}},
        )

    async def update_status(self, user_id: str, status: str):
        await self.col.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"status": status, "updated_at": datetime.now(timezone.utc)}},
        )

    async def unlock_if_expired(self, user: dict) -> dict:
        if user.get("is_locked") and user.get("locked_until"):
            if datetime.now(timezone.utc) > user["locked_until"].replace(tzinfo=timezone.utc):
                await self.col.update_one(
                    {"_id": ObjectId(user["id"])},
                    {"$set": {"is_locked": False, "locked_until": None, "failed_attempts": 0, "status": "active"}},
                )
                user["is_locked"] = False
                user["status"] = "active"
        return user

    async def create_indexes(self):
        await self.col.create_index("email", unique=True, sparse=True)
        await self.col.create_index("mobile", unique=True, sparse=True)

    async def list_users(self, owner_id: Optional[str] = None, skip: int = 0, limit: int = 50) -> List[dict]:
        query: dict[str, object] = {"deleted_at": None}
        if owner_id:
            query["owner_id"] = owner_id
        cursor = self.col.find(query, {"password_hash": 0}).skip(skip).limit(limit)
        return [self._serialize(d) async for d in cursor]

    async def count_users(self, owner_id: Optional[str] = None) -> int:
        query: dict[str, object] = {"deleted_at": None}
        if owner_id:
            query["owner_id"] = owner_id
        return await self.col.count_documents(query)

    async def update_fields(self, user_id: str, fields: dict, updated_by: str):
        fields["updated_at"] = datetime.now(timezone.utc)
        fields["updated_by"] = updated_by
        await self.col.update_one({"_id": ObjectId(user_id)}, {"$set": fields})

    async def soft_delete(self, user_id: str, deleted_by: str):
        await self.col.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "deleted_at": datetime.now(timezone.utc),
                "status": "deleted",
                "updated_by": deleted_by,
            }},
        )
