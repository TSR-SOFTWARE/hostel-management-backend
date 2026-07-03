"""
Migration runner — Flyway-style versioned migrations for MongoDB.

Convention: files in versions/ must be named V{n}__{description}.py
Each file must expose:  async def up(db)  and  async def down(db)

Applied migrations are tracked in the `schema_migrations` collection.
Running this script is idempotent — already-applied versions are skipped.
"""
import asyncio
import importlib
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient

# Allow running as  python -m app.migrations.migrator
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.core.config import settings

VERSIONS_DIR = Path(__file__).parent / "versions"
VERSION_PATTERN = re.compile(r"^V(\d+)__(.+)\.py$")
MIGRATIONS_COLLECTION = "schema_migrations"


def _discover() -> list[tuple[int, str, Path]]:
    """Return sorted list of (version_number, description, path)."""
    migrations = []
    for f in VERSIONS_DIR.glob("V*__*.py"):
        m = VERSION_PATTERN.match(f.name)
        if m:
            migrations.append((int(m.group(1)), m.group(2), f))
    return sorted(migrations, key=lambda x: x[0])


async def _applied_versions(db) -> set[int]:
    cursor = db[MIGRATIONS_COLLECTION].find({}, {"version": 1})
    return {doc["version"] async for doc in cursor}


async def _record(db, version: int, description: str, success: bool, error: str = ""):
    await db[MIGRATIONS_COLLECTION].insert_one({
        "version": version,
        "description": description,
        "applied_at": datetime.now(timezone.utc),
        "success": success,
        "error": error,
    })


async def migrate(db):
    migrations = _discover()
    if not migrations:
        print("No migration files found.")
        return

    applied = await _applied_versions(db)
    pending = [(v, d, p) for v, d, p in migrations if v not in applied]

    if not pending:
        print("All migrations already applied. Nothing to do.")
        return

    print(f"Found {len(pending)} pending migration(s):")
    for version, description, path in pending:
        label = f"V{version}__{description}"
        print(f"  Applying {label} ...")
        spec = importlib.util.spec_from_file_location(label, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        try:
            await module.up(db)
            await _record(db, version, description, success=True)
            print(f"  ✓ {label} applied")
        except Exception as e:
            await _record(db, version, description, success=False, error=str(e))
            print(f"  ✗ {label} FAILED: {e}")
            raise SystemExit(1)

    print("\nAll migrations applied successfully.")


async def main():
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.DB_NAME]
    try:
        await migrate(db)
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
