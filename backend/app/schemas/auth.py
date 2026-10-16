from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    tenant_name: str = Field(min_length=2, max_length=150)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class PasswordResetRequestCreate(BaseModel):
    email: EmailStr


class PasswordResetCompleteRequest(BaseModel):
    token: str = Field(min_length=32, max_length=256)
    password: str = Field(min_length=8, max_length=128)


class PasswordResetRequestResponse(BaseModel):
    id: UUID
    email: EmailStr
    status: str
    requested_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PasswordResetStatusResponse(BaseModel):
    is_platform_super_admin: bool


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    first_name: str
    last_name: str | None
    is_active: bool
    is_verified: bool

    model_config = ConfigDict(from_attributes=True)


class TenantResponse(BaseModel):
    id: UUID
    name: str

    model_config = ConfigDict(from_attributes=True)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    tenant: TenantResponse