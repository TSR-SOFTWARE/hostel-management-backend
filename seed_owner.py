"""
Standalone script to seed the default owner user directly into Atlas.
Run: python seed_owner.py
"""
import asyncio
import bcrypt
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone

# ── Config ────────────────────────────────────────────────────────────────────
MONGO_URI = "mongodb+srv://tsrsoftwarehyd_db_user:Pass1234@cluster-tsh.n5sxgmz.mongodb.net/hostel_management?retryWrites=true&w=majority&appName=cluster-tsh"
DB_NAME = "hostel_management"
DEFAULT_EMAIL = "owner@hostel.com"
DEFAULT_MOBILE = "9999999999"
DEFAULT_PASSWORD = "Owner@1234"
# ─────────────────────────────────────────────────────────────────────────────


async def seed():
    print(f"Connecting to Atlas...")
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]

    # Verify connection
    await db.command("ping")
    print("Connected successfully.\n")

    # Check existing user
    existing = await db["users"].find_one({"email": DEFAULT_EMAIL})
    if existing:
        print(f"Owner user already exists: {DEFAULT_EMAIL}")
        print(f"User ID: {existing['_id']}")
        print(f"Status : {existing['status']}")
        client.close()
        return

    # Find Owner role
    owner_role = await db["roles"].find_one({"role_name": "Owner"})
    if not owner_role:
        print("ERROR: Owner role not found.")
        print("Roles in DB:")
        async for r in db["roles"].find({}, {"role_name": 1}):
            print(f"  - {r['role_name']} ({r['_id']})")
        client.close()
        return

    print(f"Found Owner role: {owner_role['_id']}")

    # Create user
    now = datetime.now(timezone.utc)
    pwd_hash = bcrypt.hashpw(DEFAULT_PASSWORD.encode(), bcrypt.gensalt()).decode()

    user_doc = {
        "owner_id": None,
        "employee_id": None,
        "first_name": "Super",
        "last_name": "Owner",
        "email": DEFAULT_EMAIL,
        "mobile": DEFAULT_MOBILE,
        "password_hash": pwd_hash,
        "role_id": str(owner_role["_id"]),
        "status": "active",
        "last_login": None,
        "failed_attempts": 0,
        "is_locked": False,
        "locked_until": None,
        "is_email_verified": True,
        "is_mobile_verified": True,
        "created_at": now,
        "created_by": None,
        "updated_at": now,
        "updated_by": None,
        "deleted_at": None,
    }

    result = await db["users"].insert_one(user_doc)
    user_id = str(result.inserted_id)

    # Save password history
    await db["password_history"].insert_one({
        "user_id": user_id,
        "password_hash": pwd_hash,
        "created_at": now,
    })

    print(f"\nOwner user created successfully!")
    print(f"  Email   : {DEFAULT_EMAIL}")
    print(f"  Mobile  : {DEFAULT_MOBILE}")
    print(f"  Password: {DEFAULT_PASSWORD}")
    print(f"  User ID : {user_id}")

    client.close()


if __name__ == "__main__":
    asyncio.run(seed())
