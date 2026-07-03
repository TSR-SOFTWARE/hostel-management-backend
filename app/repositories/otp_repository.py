from datetime import datetime, timezone
from bson import ObjectId
from typing import Optional


class OtpRepository:
    def __init__(self, db):
        self.col = db["otp_requests"]

    async def insert(self, doc: dict) -> str:
        result = await self.col.insert_one(doc)
        return str(result.inserted_id)

    async def find_latest(self, user_id: str, purpose: str) -> Optional[dict]:
        doc = await self.col.find_one(
            {"user_id": user_id, "purpose": purpose, "is_used": False},
            sort=[("created_at", -1)],
        )
        if doc:
            doc["id"] = str(doc.pop("_id"))
        return doc

    async def increment_attempts(self, otp_id: str):
        await self.col.update_one({"_id": ObjectId(otp_id)}, {"$inc": {"attempts": 1}})

    async def mark_used(self, otp_id: str):
        await self.col.update_one({"_id": ObjectId(otp_id)}, {"$set": {"is_used": True}})

    async def create_indexes(self):
        await self.col.create_index([("user_id", 1), ("purpose", 1)])
