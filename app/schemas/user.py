from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from app.models.user import UserRole


# Base schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)


# Create schemas
class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class AdminUserCreate(UserBase):
    """Schema for admin to create users with role."""
    password: str = Field(..., min_length=8)
    role: UserRole = Field(default=UserRole.USER)
    is_active: bool = Field(default=True)


class UserLogin(BaseModel):
    identifier: str = Field(..., description="Email или username для входа")
    password: str


# Update schemas
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


# Response schemas
class UserResponse(UserBase):
    id: int
    role: UserRole
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserWithStats(UserResponse):
    items_count: int = 0
    orders_count: int = 0


# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
