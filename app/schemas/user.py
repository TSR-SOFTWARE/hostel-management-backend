from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr
from app.core.security import validate_password_strength
from pydantic import field_validator
from app.models.user import UserStatus


class CreateUserRequest(BaseModel):
    first_name: str
    last_name: str
    email: Optional[EmailStr] = None
    mobile: Optional[str] = None
    password: str
    role_id: str
    owner_id: Optional[str] = None
    employee_id: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if not validate_password_strength(v):
            raise ValueError(
                "Password must be 8+ chars with uppercase, lowercase, number, and special character"
            )
        return v


class UpdateUserRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role_id: Optional[str] = None
    status: Optional[UserStatus] = None
    mobile: Optional[str] = None


class UserDetailResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: Optional[str] = None
    mobile: Optional[str] = None
    role_id: str
    owner_id: Optional[str] = None
    employee_id: Optional[str] = None
    status: str
    is_email_verified: bool
    is_mobile_verified: bool
    last_login: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
