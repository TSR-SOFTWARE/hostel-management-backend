"""
Seed script: Creates default roles, permissions, role-permission mappings,
and a default Owner user.

Run: python -m app.migrations.seed
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.core.security import hash_password
from app.models.role import role_document, permission_document, role_permission_document
from app.models.user import user_document
from app.models.password_history import password_history_document

ROLES = [
    ("Owner", "Hostel owner with full access", True),
    ("Manager", "Manages day-to-day operations", True),
    ("Supervisor", "Supervises staff and students", True),
    ("Chef", "Manages kitchen and meals", True),
    ("Cleaning Head", "Manages cleaning staff", True),
    ("Helper", "General helper role", True),
]

PERMISSIONS = [
    ("Student", "Create"), ("Student", "Read"), ("Student", "Update"), ("Student", "Delete"),
    ("Employee", "Create"), ("Employee", "Read"), ("Employee", "Update"), ("Employee", "Delete"),
    ("Expense", "Create"), ("Expense", "Read"), ("Expense", "Update"), ("Expense", "Approve"),
    ("Hostel", "Create"), ("Hostel", "Read"), ("Hostel", "Update"), ("Hostel", "Delete"),
    ("Role", "Create"), ("Role", "Read"), ("Role", "Update"),
    ("User", "Create"), ("User", "Read"), ("User", "Update"), ("User", "Delete"),
    ("Report", "Read"),
    ("Inventory", "Create"), ("Inventory", "Read"), ("Inventory", "Update"),
]

# Role -> list of (module, action) it gets
ROLE_PERMISSIONS = {
    "Owner": [(m, a) for m, a in PERMISSIONS],  # All permissions
    "Manager": [
        ("Student", "Create"), ("Student", "Read"), ("Student", "Update"),
        ("Employee", "Read"), ("Employee", "Update"),
        ("Expense", "Create"), ("Expense", "Read"), ("Expense", "Approve"),
        ("Hostel", "Read"), ("Report", "Read"),
        ("Inventory", "Create"), ("Inventory", "Read"), ("Inventory", "Update"),
    ],
    "Supervisor": [
        ("Student", "Read"), ("Student", "Update"),
        ("Employee", "Read"),
        ("Expense", "Read"),
        ("Hostel", "Read"),
    ],
    "Chef": [("Inventory", "Read"), ("Inventory", "Update")],
    "Cleaning Head": [("Employee", "Read")],
    "Helper": [],
}

DEFAULT_OWNER_PASSWORD = "Owner@1234"


async def seed():
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.DB_NAME]

    # Drop existing seed collections for idempotency
    for col in ["roles", "permissions", "role_permissions", "users", "password_history"]:
        await db[col].drop()

    # Insert roles
    role_ids = {}
    for name, desc, is_sys in ROLES:
        result = await db["roles"].insert_one(role_document(name, desc, is_sys))
        role_ids[name] = str(result.inserted_id)
        print(f"  Role created: {name} -> {role_ids[name]}")

    # Insert permissions
    perm_ids = {}
    for module, action in PERMISSIONS:
        result = await db["permissions"].insert_one(
            permission_document(module, action, f"{action} {module}")
        )
        perm_ids[(module, action)] = str(result.inserted_id)

    print(f"  {len(perm_ids)} permissions created")

    # Assign role permissions
    for role_name, perms in ROLE_PERMISSIONS.items():
        role_id = role_ids[role_name]
        for module, action in perms:
            perm_id = perm_ids.get((module, action))
            if perm_id:
                await db["role_permissions"].insert_one(role_permission_document(role_id, perm_id))
    print("  Role-permission mappings created")

    # Create default Owner user
    owner_role_id = role_ids["Owner"]
    pwd_hash = hash_password(DEFAULT_OWNER_PASSWORD)
    user_doc = user_document(
        owner_id=None,
        employee_id=None,
        first_name="Super",
        last_name="Owner",
        email="owner@hostel.com",
        mobile="9999999999",
        password_hash=pwd_hash,
        role_id=owner_role_id,
    )
    user_doc["status"] = "active"
    user_doc["is_email_verified"] = True
    user_doc["is_mobile_verified"] = True

    user_result = await db["users"].insert_one(user_doc)
    user_id = str(user_result.inserted_id)
    await db["password_history"].insert_one(password_history_document(user_id, pwd_hash))

    # Create indexes
    await db["users"].create_index("email", unique=True, sparse=True)
    await db["users"].create_index("mobile", unique=True, sparse=True)
    await db["refresh_tokens"].create_index("token_hash")
    await db["refresh_tokens"].create_index("user_id")
    await db["otp_requests"].create_index([("user_id", 1), ("purpose", 1)])
    await db["audit_logs"].create_index("user_id")
    await db["audit_logs"].create_index("created_at")

    print(f"\n  Default Owner user created:")
    print(f"    Email   : owner@hostel.com")
    print(f"    Mobile  : 9999999999")
    print(f"    Password: {DEFAULT_OWNER_PASSWORD}")
    print(f"    User ID : {user_id}")
    print("\n  Seed completed successfully!")

    client.close()


if __name__ == "__main__":
    asyncio.run(seed())
