from typing import List


class PasswordHistoryRepository:
    def __init__(self, db):
        self.col = db["password_history"]

    async def insert(self, doc: dict):
        await self.col.insert_one(doc)

    async def get_recent(self, user_id: str, count: int) -> List[dict]:
        cursor = self.col.find({"user_id": user_id}, sort=[("created_at", -1)], limit=count)
        return [d async for d in cursor]
