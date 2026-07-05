"""
V3__seed_default_owner.py
Creates the default Super Owner user if not already present.
"""
import os
from app.core.config import settings
from app.core.security import hash_password
from app.models.user import user_document
from app.models.password_history import password_history_document

DEFAULT_EMAIL = "owner@hostel.com"
DEFAULT_MOBILE = "9999999999"
DEFAULT_PASSWORD = settings.DEFAULT_OWNER_PASSWORD


async def up(db):
    existing = await db["users"].find_one({"email": DEFAULT_EMAIL})
    if existing:
        print("  [V3] Default owner already exists, skipping")
        return

    owner_role = await db["roles"].find_one({"role_name": "Owner"})
    if not owner_role:
        raise RuntimeError("Owner role not found — ensure V2 ran first")

    pwd_hash = hash_password(DEFAULT_PASSWORD)
    user_doc = user_document(
        owner_id=None,
        employee_id=None,
        first_name="Super",
        last_name="Owner",
        email=DEFAULT_EMAIL,
        mobile=DEFAULT_MOBILE,
        password_hash=pwd_hash,
        role_id=str(owner_role["_id"]),
    )
    user_doc["status"] = "active"
    user_doc["is_email_verified"] = True
    user_doc["is_mobile_verified"] = True

    result = await db["users"].insert_one(user_doc)
    user_id = str(result.inserted_id)
    await db["password_history"].insert_one(password_history_document(user_id, pwd_hash))

    print(f"  [V3] Default owner created: {DEFAULT_EMAIL} / {DEFAULT_PASSWORD}")


async def down(db):
    await db["users"].delete_one({"email": DEFAULT_EMAIL})
    print("  [V3] Default owner deleted")
