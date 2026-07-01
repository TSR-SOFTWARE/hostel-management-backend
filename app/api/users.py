from fastapi import APIRouter, Depends, Request, Query
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.schemas.auth import UserResponse, MessageResponse
from app.schemas.user import CreateUserRequest, UpdateUserRequest, UserDetailResponse
from app.repositories.role_repository import RoleRepository
from app.services.user_service import UserService

router = APIRouter(prefix="/api", tags=["Users & Roles"])


@router.get("/users/me", response_model=UserDetailResponse)
async def get_me(current_user=Depends(get_current_user)):
    current_user.pop("password_hash", None)
    return current_user


@router.post("/users", response_model=UserDetailResponse, status_code=201)
async def create_user(
    body: CreateUserRequest,
    request: Request,
    current_user=Depends(require_permission("User", "Create")),
    db=Depends(get_db),
):
    ip = request.client.host if request.client else None
    return await UserService(db).create_user(body.model_dump(), current_user["id"], ip)


@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    owner_id: str = Query(None),
    current_user=Depends(require_permission("User", "Read")),
    db=Depends(get_db),
):
    return await UserService(db).list_users(owner_id=owner_id, page=page, limit=limit)


@router.get("/users/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: str,
    current_user=Depends(require_permission("User", "Read")),
    db=Depends(get_db),
):
    return await UserService(db).get_user(user_id)


@router.patch("/users/{user_id}", response_model=UserDetailResponse)
async def update_user(
    user_id: str,
    body: UpdateUserRequest,
    request: Request,
    current_user=Depends(require_permission("User", "Update")),
    db=Depends(get_db),
):
    ip = request.client.host if request.client else None
    return await UserService(db).update_user(user_id, body.model_dump(), current_user["id"], ip)


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: str,
    request: Request,
    current_user=Depends(require_permission("User", "Delete")),
    db=Depends(get_db),
):
    ip = request.client.host if request.client else None
    await UserService(db).delete_user(user_id, current_user["id"], ip)
    return {"message": "User deleted successfully"}


@router.get("/roles")
async def list_roles(current_user=Depends(get_current_user), db=Depends(get_db)):
    return await RoleRepository(db).list_roles()


@router.get("/permissions")
async def list_permissions(current_user=Depends(get_current_user), db=Depends(get_db)):
    return await RoleRepository(db).list_permissions()
