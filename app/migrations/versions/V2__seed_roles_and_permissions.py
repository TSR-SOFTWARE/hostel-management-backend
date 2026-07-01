"""
V2__seed_roles_and_permissions.py
Seeds system roles and their permissions.
"""
from app.models.role import role_document, permission_document, role_permission_document

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

ROLE_PERMISSIONS = {
    "Owner": [(m, a) for m, a in PERMISSIONS],
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


async def up(db):
    role_ids = {}
    for name, desc, is_sys in ROLES:
        existing = await db["roles"].find_one({"role_name": name})
        if existing:
            role_ids[name] = str(existing["_id"])
            continue
        result = await db["roles"].insert_one(role_document(name, desc, is_sys))
        role_ids[name] = str(result.inserted_id)

    perm_ids = {}
    for module, action in PERMISSIONS:
        existing = await db["permissions"].find_one({"module": module, "action": action})
        if existing:
            perm_ids[(module, action)] = str(existing["_id"])
            continue
        result = await db["permissions"].insert_one(
            permission_document(module, action, f"{action} {module}")
        )
        perm_ids[(module, action)] = str(result.inserted_id)

    for role_name, perms in ROLE_PERMISSIONS.items():
        role_id = role_ids[role_name]
        for module, action in perms:
            perm_id = perm_ids.get((module, action))
            if perm_id:
                exists = await db["role_permissions"].find_one(
                    {"role_id": role_id, "permission_id": perm_id}
                )
                if not exists:
                    await db["role_permissions"].insert_one(
                        role_permission_document(role_id, perm_id)
                    )

    print(f"  [V2] {len(ROLES)} roles, {len(PERMISSIONS)} permissions seeded")


async def down(db):
    await db["role_permissions"].drop()
    await db["permissions"].drop()
    await db["roles"].drop()
    print("  [V2] Roles and permissions dropped")
