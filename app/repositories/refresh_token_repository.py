from datetime import datetime, timezone
from bson import ObjectId
from typing import Optional


class RefreshTokenRepository:
    def __init__(self, db):
        self.col = db["refresh_tokens"]

    async def insert(self, doc: dict) -> str:
        result = await self.col.insert_one(doc)
        return str(result.inserted_id)

    async def find_active(self, token_hash: str) -> Optional[dict]:
        doc = await self.col.find_one({"token_hash": token_hash, "revoked_at": None})
        if doc:
            doc["id"] = str(doc.pop("_id"))
        return doc

    async def revoke(self, token_hash: str):
        await self.col.update_one(
            {"token_hash": token_hash},
            {"$set": {"revoked_at": datetime.now(timezone.utc)}},
        )

    async def revoke_all_for_user(self, user_id: str):
        await self.col.update_many(
            {"user_id": user_id, "revoked_at": None},
            {"$set": {"revoked_at": datetime.now(timezone.utc)}},
        )

    async def create_indexes(self):
        await self.col.create_index("token_hash")
        await self.col.create_index("user_id")
