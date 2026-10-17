from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)


MembershipStatus = Literal["active", "suspended"]


class TeamMemberResponse(BaseModel):
    id: UUID
    email: EmailStr
    first_name: str
    last_name: str | None
    role: str
    role_id: UUID
    membership_status: str
    is_active: bool
    is_verified: bool
    # When the user joined this workspace (membership creation time).
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TeamMemberListResponse(BaseModel):
    items: list[TeamMemberResponse]
    total: int
    page: int
    page_size: int


class RoleResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    # Whether the requesting member may assign or manage this role, per the
    # existing privilege rules. The backend remains the final authority.
    assignable: bool

    model_config = ConfigDict(from_attributes=True)


class InviteTeamMemberRequest(BaseModel):
    email: EmailStr
    role_id: UUID

    model_config = ConfigDict(extra="forbid")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class InvitationResponse(BaseModel):
    id: UUID
    email: EmailStr
    role: str
    role_id: UUID
    expires_at: datetime
    created_at: datetime
    # Only returned by POST /users/invite in development, until email
    # delivery exists. Never returned anywhere else.
    invitation_token: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UpdateTeamMemberRequest(BaseModel):
    role_id: UUID | None = None
    status: MembershipStatus | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_fields(self) -> "UpdateTeamMemberRequest":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")

        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")

        return self


class InvitationAcceptRequest(BaseModel):
    token: str = Field(min_length=20, max_length=128)
    password: str = Field(min_length=8, max_length=128)
    # Required only when the invited email has no account yet.
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)

    model_config = ConfigDict(extra="forbid")

    @field_validator("first_name", "last_name")
    @classmethod
    def strip_names(cls, value: str | None) -> str | None:
        if value is None:
            return None

        return value.strip() or None
