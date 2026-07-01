"""
V1__create_indexes.py
Creates all required MongoDB indexes.
"""


async def up(db):
    await db["users"].create_index("email", unique=True, sparse=True)
    await db["users"].create_index("mobile", unique=True, sparse=True)
    await db["refresh_tokens"].create_index("token_hash")
    await db["refresh_tokens"].create_index("user_id")
    await db["otp_requests"].create_index([("user_id", 1), ("purpose", 1)])
    await db["audit_logs"].create_index("user_id")
    await db["audit_logs"].create_index("created_at")
    print("  [V1] Indexes created")


async def down(db):
    await db["users"].drop_index("email_1")
    await db["users"].drop_index("mobile_1")
    await db["refresh_tokens"].drop_index("token_hash_1")
    await db["refresh_tokens"].drop_index("user_id_1")
    await db["otp_requests"].drop_index("user_id_1_purpose_1")
    await db["audit_logs"].drop_index("user_id_1")
    await db["audit_logs"].drop_index("created_at_1")
    print("  [V1] Indexes dropped")
