from bson import ObjectId
from typing import Optional


class RoleRepository:
    def __init__(self, db):
        self.roles = db["roles"]
        self.permissions = db["permissions"]
        self.role_permissions = db["role_permissions"]

    def _serialize(self, doc: dict) -> dict:
        if doc:
            doc["id"] = str(doc.pop("_id"))
        return doc

    async def find_by_id(self, role_id: str) -> Optional[dict]:
        doc = await self.roles.find_one({"_id": ObjectId(role_id)})
        return self._serialize(doc) if doc else None

    async def find_by_name(self, name: str) -> Optional[dict]:
        doc = await self.roles.find_one({"role_name": name})
        return self._serialize(doc) if doc else None

    async def list_roles(self) -> list:
        cursor = self.roles.find({})
        return [self._serialize(d) async for d in cursor]

    async def list_permissions(self) -> list:
        cursor = self.permissions.find({})
        return [self._serialize(d) async for d in cursor]

    async def has_permission(self, role_id: str, module: str, action: str) -> bool:
        perm = await self.permissions.find_one({"module": module, "action": action})
        if not perm:
            return False
        rp = await self.role_permissions.find_one(
            {"role_id": role_id, "permission_id": str(perm["_id"])}
        )
        return rp is not None

    async def insert_role(self, doc: dict) -> str:
        result = await self.roles.insert_one(doc)
        return str(result.inserted_id)

    async def insert_permission(self, doc: dict) -> str:
        result = await self.permissions.insert_one(doc)
        return str(result.inserted_id)

    async def insert_role_permission(self, doc: dict):
        await self.role_permissions.insert_one(doc)

    async def get_role_permission_ids(self, role_id: str) -> list:
        cursor = self.role_permissions.find({"role_id": role_id})
        return [doc["permission_id"] async for doc in cursor]

    async def set_role_permissions(self, role_id: str, permission_ids: list):
        await self.role_permissions.delete_many({"role_id": role_id})
        if permission_ids:
            docs = [{"role_id": role_id, "permission_id": pid} for pid in permission_ids]
            await self.role_permissions.insert_many(docs)

    async def update_role(self, role_id: str, fields: dict):
        from bson import ObjectId
        from datetime import datetime, timezone
        fields["updated_at"] = datetime.now(timezone.utc)
        await self.roles.update_one({"_id": ObjectId(role_id)}, {"$set": fields})

    async def delete_role(self, role_id: str):
        from bson import ObjectId
        await self.roles.delete_one({"_id": ObjectId(role_id)})
        await self.role_permissions.delete_many({"role_id": role_id})
