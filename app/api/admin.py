from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, Request, Query, HTTPException, status
from pydantic import BaseModel, EmailStr
from app.core.database import get_db
from app.core.dependencies import require_permission, get_current_user
from app.repositories.role_repository import RoleRepository
from app.models.role import role_document
from app.services.hostel_service import HostelService

router = APIRouter(prefix="/api/admin", tags=["Admin"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class CreateRoleRequest(BaseModel):
    role_name: str
    description: str = ""


class UpdateRoleRequest(BaseModel):
    role_name: Optional[str] = None
    description: Optional[str] = None


class SetPermissionsRequest(BaseModel):
    permission_ids: List[str]


class CreateHostelRequest(BaseModel):
    name: str
    address: str
    city: str
    state: str
    pincode: str
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    total_rooms: int
    owner_id: Optional[str] = None


class UpdateHostelRequest(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    total_rooms: Optional[int] = None
    is_active: Optional[bool] = None


# ── Role endpoints ─────────────────────────────────────────────────────────────

@router.post("/roles", status_code=201)
async def create_role(
    body: CreateRoleRequest,
    current_user=Depends(require_permission("Role", "Create")),
    db=Depends(get_db),
):
    repo = RoleRepository(db)
    existing = await repo.find_by_name(body.role_name)
    if existing:
        raise HTTPException(status_code=400, detail="Role with this name already exists")
    doc = role_document(body.role_name, body.description, is_system_role=False)
    role_id = await repo.insert_role(doc)
    return {"id": role_id, **doc, "created_at": doc["created_at"].isoformat()}


@router.patch("/roles/{role_id}")
async def update_role(
    role_id: str,
    body: UpdateRoleRequest,
    current_user=Depends(require_permission("Role", "Update")),
    db=Depends(get_db),
):
    repo = RoleRepository(db)
    role = await repo.find_by_id(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if fields:
        await repo.update_role(role_id, fields)
    return await repo.find_by_id(role_id)


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: str,
    current_user=Depends(require_permission("Role", "Update")),
    db=Depends(get_db),
):
    repo = RoleRepository(db)
    role = await repo.find_by_id(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if role.get("is_system_role"):
        raise HTTPException(status_code=400, detail="System roles cannot be deleted")
    await repo.delete_role(role_id)
    return {"message": "Role deleted successfully"}


# ── Role-Permission assignment ─────────────────────────────────────────────────

@router.get("/roles/{role_id}/permissions")
async def get_role_permissions(
    role_id: str,
    current_user=Depends(require_permission("Role", "Read")),
    db=Depends(get_db),
):
    repo = RoleRepository(db)
    role = await repo.find_by_id(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    permission_ids = await repo.get_role_permission_ids(role_id)
    return {"role_id": role_id, "permission_ids": permission_ids}


@router.put("/roles/{role_id}/permissions")
async def set_role_permissions(
    role_id: str,
    body: SetPermissionsRequest,
    current_user=Depends(require_permission("Role", "Update")),
    db=Depends(get_db),
):
    repo = RoleRepository(db)
    role = await repo.find_by_id(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    await repo.set_role_permissions(role_id, body.permission_ids)
    return {"message": "Permissions updated successfully"}


# ── Hostel endpoints ───────────────────────────────────────────────────────────

@router.post("/hostels", status_code=201)
async def create_hostel(
    body: CreateHostelRequest,
    current_user=Depends(require_permission("Hostel", "Create")),
    db=Depends(get_db),
):
    return await HostelService(db).create_hostel(body.model_dump(), current_user["id"])


@router.get("/hostels")
async def list_hostels(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    owner_id: Optional[str] = Query(None),
    current_user=Depends(require_permission("Hostel", "Read")),
    db=Depends(get_db),
):
    return await HostelService(db).list_hostels(owner_id=owner_id, page=page, limit=limit)


@router.get("/hostels/{hostel_id}")
async def get_hostel(
    hostel_id: str,
    current_user=Depends(require_permission("Hostel", "Read")),
    db=Depends(get_db),
):
    return await HostelService(db).get_hostel(hostel_id)


@router.patch("/hostels/{hostel_id}")
async def update_hostel(
    hostel_id: str,
    body: UpdateHostelRequest,
    current_user=Depends(require_permission("Hostel", "Update")),
    db=Depends(get_db),
):
    return await HostelService(db).update_hostel(hostel_id, body.model_dump(), current_user["id"])


@router.delete("/hostels/{hostel_id}")
async def delete_hostel(
    hostel_id: str,
    current_user=Depends(require_permission("Hostel", "Delete")),
    db=Depends(get_db),
):
    await HostelService(db).delete_hostel(hostel_id, current_user["id"])
    return {"message": "Hostel deleted successfully"}
