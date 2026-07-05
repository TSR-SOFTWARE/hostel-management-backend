from fastapi import APIRouter, Depends, Request
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.auth import (
    LoginRequest, RefreshTokenRequest, ForgotPasswordRequest,
    VerifyOtpRequest, ResetPasswordRequest, ChangePasswordRequest,
    TokenResponse, MessageResponse, UserResponse,
)
from app.services.auth_service import AuthService
from app.services.otp_service import OtpService
from app.services.password_service import PasswordService
from app.models.otp_request import OtpPurpose

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, db=Depends(get_db)):
    return await AuthService(db).login(body.identifier, body.password, request)


@router.post("/logout", response_model=MessageResponse)
async def logout(body: RefreshTokenRequest, request: Request, current_user=Depends(get_current_user), db=Depends(get_db)):
    await AuthService(db).logout(body.refresh_token, current_user["id"], request)
    return {"message": "Logged out successfully"}


@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_token(body: RefreshTokenRequest, db=Depends(get_db)):
    return await AuthService(db).refresh_access_token(body.refresh_token)


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(body: ForgotPasswordRequest, db=Depends(get_db)):
    msg = await OtpService(db).send_otp(body.identifier, OtpPurpose.forgot_password)
    return {"message": msg}


@router.post("/verify-otp", response_model=MessageResponse)
async def verify_otp(body: VerifyOtpRequest, db=Depends(get_db)):
    await OtpService(db).verify_otp(body.identifier, body.otp, body.purpose, mark_used=False)
    return {"message": "OTP verified successfully"}


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(body: ResetPasswordRequest, request: Request, db=Depends(get_db)):
    user_id = await OtpService(db).verify_otp(body.identifier, body.otp, OtpPurpose.forgot_password, mark_used=True)
    await PasswordService(db).reset_password(user_id, body.new_password, request)
    return {"message": "Password reset successfully. Please login again."}


@router.post("/change-password", response_model=MessageResponse)
async def change_password(body: ChangePasswordRequest, request: Request, current_user=Depends(get_current_user), db=Depends(get_db)):
    await PasswordService(db).change_password(current_user["id"], body.old_password, body.new_password, request)
    return {"message": "Password changed successfully. Please login again."}
