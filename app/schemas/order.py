from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from app.models.order import OrderStatus
from app.schemas.item import ItemResponse


class OrderItemResponse(BaseModel):
    id: int
    item_id: int
    quantity: int
    price_at_purchase: float
    item: ItemResponse
    
    class Config:
        from_attributes = True


class OrderCreate(BaseModel):
    shipping_address: Optional[str] = None


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderResponse(BaseModel):
    id: int
    user_id: int
    total_price: float
    status: OrderStatus
    shipping_address: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class OrderDetailResponse(OrderResponse):
    items: List[OrderItemResponse]


class OrderListResponse(BaseModel):
    orders: List[OrderResponse]
    total: int
    page: int
    pages: int
