from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = None


class CategoryCreate(CategoryBase):
    slug: Optional[str] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = None
    slug: Optional[str] = None


class CategoryResponse(CategoryBase):
    id: int
    slug: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class CategoryWithCount(CategoryResponse):
    items_count: int = 0
