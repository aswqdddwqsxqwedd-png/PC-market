from pydantic import BaseModel
from typing import Any, Optional, Dict, Generic, TypeVar, List
from datetime import datetime

T = TypeVar('T')


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class SuccessResponse(BaseModel):
    success: bool = True
    message: str


class PaginationParams(BaseModel):
    page: int = 1
    limit: int = 10
    sort_by: str = "created_at"
    sort_order: str = "desc"


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    limit: int
    pages: int


# Stats for admin
class DashboardStats(BaseModel):
    total_users: int
    total_items: int
    total_orders: int
    total_categories: int
    total_revenue: float
    recent_orders: int
    active_items: int


class UserStats(BaseModel):
    total: int
    active: int
    new_today: int
    by_role: Dict[str, int]


class ItemStats(BaseModel):
    total: int
    active: int
    by_category: Dict[str, int]
    avg_price: float


class OrderStats(BaseModel):
    total: int
    by_status: Dict[str, int]
    total_revenue: float
    avg_order_value: float
