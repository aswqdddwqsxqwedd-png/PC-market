from pydantic import BaseModel, Field
from typing import List
from datetime import datetime
from app.schemas.item import ItemResponse


class CartItemCreate(BaseModel):
    item_id: int
    quantity: int = Field(default=1, ge=1)


class CartItemUpdate(BaseModel):
    quantity: int = Field(..., ge=1)


class CartItemResponse(BaseModel):
    id: int
    item_id: int
    quantity: int
    added_at: datetime
    item: ItemResponse
    
    class Config:
        from_attributes = True


class CartResponse(BaseModel):
    items: List[CartItemResponse]
    total_items: int
    total_price: float
