from fastapi import HTTPException, status
from app.repositories.hostel_repository import HostelRepository
from app.models.hostel import hostel_document


class HostelService:
    def __init__(self, db):
        self.repo = HostelRepository(db)

    async def create_hostel(self, data: dict, created_by: str) -> dict:
        doc = hostel_document(
            owner_id=data.get("owner_id") or created_by,
            name=data["name"],
            address=data["address"],
            city=data["city"],
            state=data["state"],
            pincode=data["pincode"],
            phone=data.get("phone"),
            email=data.get("email"),
            total_rooms=data["total_rooms"],
            created_by=created_by,
        )
        hostel_id = await self.repo.insert(doc)
        return await self._get_or_404(hostel_id)

    async def list_hostels(self, owner_id=None, page: int = 1, limit: int = 50) -> dict:
        skip = (page - 1) * limit
        hostels = await self.repo.list_hostels(owner_id=owner_id, skip=skip, limit=limit)
        total = await self.repo.count(owner_id=owner_id)
        return {"total": total, "page": page, "limit": limit, "hostels": hostels}

    async def get_hostel(self, hostel_id: str) -> dict:
        return await self._get_or_404(hostel_id)

    async def update_hostel(self, hostel_id: str, data: dict, updated_by: str) -> dict:
        await self._get_or_404(hostel_id)
        fields = {k: v for k, v in data.items() if v is not None}
        await self.repo.update_fields(hostel_id, fields, updated_by)
        return await self._get_or_404(hostel_id)

    async def delete_hostel(self, hostel_id: str, deleted_by: str):
        await self._get_or_404(hostel_id)
        await self.repo.soft_delete(hostel_id, deleted_by)

    async def _get_or_404(self, hostel_id: str) -> dict:
        hostel = await self.repo.find_by_id(hostel_id)
        if not hostel:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hostel not found")
        return hostel
