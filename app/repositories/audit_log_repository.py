class AuditLogRepository:
    def __init__(self, db):
        self.col = db["audit_logs"]

    async def insert(self, doc: dict):
        await self.col.insert_one(doc)

    async def create_indexes(self):
        await self.col.create_index("user_id")
        await self.col.create_index("created_at")
