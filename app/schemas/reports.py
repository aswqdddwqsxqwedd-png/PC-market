"""Schemas for reports and analytics."""
from pydantic import BaseModel
from typing import List, Optional, Dict
from app.models import UserRole, OrderStatus


class UserStats(BaseModel):
    """Statistics for a single user."""
    id: int
    username: str
    email: str
    role: str
    order_count: int
    total_spent: float


class ActiveUsersReport(BaseModel):
    """Report on active users."""
    period_days: int
    active_users: int
    new_users: int
    total_users: int
    users_by_role: Dict[str, int]
    top_users: List[UserStats]


class ItemStats(BaseModel):
    """Statistics for a single item."""
    id: int
    name: str
    price: float
    sold_quantity: int
    revenue: float


class CategoryItemStats(BaseModel):
    """Item statistics by category."""
    category_id: int
    category_name: str
    item_count: int
    in_stock_count: int


class ItemsReport(BaseModel):
    """Report on items and sales."""
    period_days: int
    total_items: int
    in_stock: int
    out_of_stock: int
    total_revenue: float
    top_selling_items: List[ItemStats]
    items_by_category: List[CategoryItemStats]


class CategoryStats(BaseModel):
    """Statistics for a category."""
    id: int
    name: str
    slug: str
    description: Optional[str]
    item_count: int
    in_stock_count: int
    orders_count: int
    items_sold: int
    revenue: float


class CategoriesReport(BaseModel):
    """Report on categories popularity."""
    total_categories: int
    categories: List[CategoryStats]
    popular_categories: List[CategoryStats]
    top_revenue_categories: List[CategoryStats]


class StatusStats(BaseModel):
    """Statistics for order status."""
    count: int
    revenue: float


class SalesReport(BaseModel):
    """Sales report."""
    period_days: int
    total_orders: int
    total_revenue: float
    average_order_value: float
    orders_by_status: Dict[str, StatusStats]

