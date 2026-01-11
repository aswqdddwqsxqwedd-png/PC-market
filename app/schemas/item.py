from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.schemas.category import CategoryResponse
from app.schemas.user import UserResponse


class ItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    quantity: int = Field(default=1, ge=0)
    image_url: Optional[str] = None


class ItemCreate(ItemBase):
    category_id: int


class ItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    quantity: Optional[int] = Field(None, ge=0)
    image_url: Optional[str] = None
    category_id: Optional[int] = None
    is_active: Optional[bool] = None


class ItemResponse(ItemBase):
    id: int
    category_id: int
    owner_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ItemDetailResponse(ItemResponse):
    category: CategoryResponse
    owner: UserResponse


class ItemListResponse(BaseModel):
    items: List[ItemResponse]
    total: int
    page: int
    pages: int
    has_next: bool
    has_prev: bool


# Filters
class ItemFilter(BaseModel):
    category_id: Optional[int] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    search: Optional[str] = None
    owner_id: Optional[int] = None
    is_active: Optional[bool] = True
