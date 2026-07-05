from datetime import datetime, timezone
from bson import ObjectId
from typing import Optional


class HostelRepository:
    def __init__(self, db):
        self.col = db["hostels"]

    def _serialize(self, doc: dict) -> dict:
        if doc:
            doc["id"] = str(doc.pop("_id"))
        return doc

    async def insert(self, doc: dict) -> str:
        result = await self.col.insert_one(doc)
        return str(result.inserted_id)

    async def find_by_id(self, hostel_id: str) -> Optional[dict]:
        doc = await self.col.find_one({"_id": ObjectId(hostel_id), "deleted_at": None})
        return self._serialize(doc) if doc else None

    async def list_hostels(self, owner_id: Optional[str] = None, skip: int = 0, limit: int = 50) -> list:
        query: dict = {"deleted_at": None}
        if owner_id:
            query["owner_id"] = owner_id
        cursor = self.col.find(query).skip(skip).limit(limit)
        return [self._serialize(d) async for d in cursor]

    async def count(self, owner_id: Optional[str] = None) -> int:
        query: dict = {"deleted_at": None}
        if owner_id:
            query["owner_id"] = owner_id
        return await self.col.count_documents(query)

    async def update_fields(self, hostel_id: str, fields: dict, updated_by: str):
        fields["updated_at"] = datetime.now(timezone.utc)
        fields["updated_by"] = updated_by
        await self.col.update_one({"_id": ObjectId(hostel_id)}, {"$set": fields})

    async def soft_delete(self, hostel_id: str, deleted_by: str):
        await self.col.update_one(
            {"_id": ObjectId(hostel_id)},
            {"$set": {
                "deleted_at": datetime.now(timezone.utc),
                "is_active": False,
                "updated_by": deleted_by,
            }},
        )
