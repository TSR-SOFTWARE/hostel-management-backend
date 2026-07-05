from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator
from app.core.security import validate_password_strength


class LoginRequest(BaseModel):
    identifier: str  # email or mobile
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    identifier: str  # email or mobile


class VerifyOtpRequest(BaseModel):
    identifier: str
    otp: str
    purpose: str = "forgot_password"


class ResetPasswordRequest(BaseModel):
    identifier: str
    otp: str
    new_password: str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v):
        if not validate_password_strength(v):
            raise ValueError(
                "Password must be 8+ chars with uppercase, lowercase, number, and special character"
            )
        return v

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v, info):
        if info.data.get("new_password") and v != info.data["new_password"]:
            raise ValueError("Passwords do not match")
        return v


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v):
        if not validate_password_strength(v):
            raise ValueError(
                "Password must be 8+ chars with uppercase, lowercase, number, and special character"
            )
        return v

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v, info):
        if info.data.get("new_password") and v != info.data["new_password"]:
            raise ValueError("Passwords do not match")
        return v


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str


class UserResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: Optional[str]
    mobile: Optional[str]
    role_id: str
    status: str
    is_email_verified: bool
    is_mobile_verified: bool
