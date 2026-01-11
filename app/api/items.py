from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.db import get_db
from app.schemas import (
    ItemCreate, ItemUpdate, ItemResponse, ItemDetailResponse, 
    ItemListResponse, ItemFilter
)
from app.services import ItemService
from app.api.deps import get_current_user, get_current_user_optional, get_current_seller_or_admin
from app.models import User, UserRole

router = APIRouter(prefix="/items", tags=["Items"])


@router.get("", response_model=ItemListResponse)
async def get_items(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category_id: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    search: Optional[str] = None,
    sort_by: str = Query("created_at", pattern="^(created_at|price|name)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db)
):
    """Get items with filtering and pagination."""
    service = ItemService(db)
    filters = ItemFilter(
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        search=search,
        is_active=True
    )
    
    skip = (page - 1) * limit
    items, total = await service.get_all(skip, limit, filters, sort_by, sort_order)
    
    pages = (total + limit - 1) // limit
    
    return ItemListResponse(
        items=items,
        total=total,
        page=page,
        pages=pages,
        has_next=page < pages,
        has_prev=page > 1
    )


@router.get("/{item_id}", response_model=ItemDetailResponse)
async def get_item(
    item_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get item by ID."""
    service = ItemService(db)
    item = await service.get_by_id(item_id)
    if not item:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Item", item_id)
    return item


@router.post("", response_model=ItemResponse, status_code=201)
async def create_item(
    item_data: ItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_seller_or_admin)
):
    """Create a new item (seller/admin only)."""
    service = ItemService(db)
    item = await service.create(item_data, current_user.id)
    return item


@router.put("/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: int,
    item_data: ItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update item (owner or admin only)."""
    service = ItemService(db)
    is_admin = current_user.role == UserRole.ADMIN
    item = await service.update(item_id, item_data, current_user.id, is_admin)
    return item


@router.delete("/{item_id}")
async def delete_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete item (owner or admin only)."""
    service = ItemService(db)
    is_admin = current_user.role == UserRole.ADMIN
    await service.delete(item_id, current_user.id, is_admin)
    return {"message": "Item deleted successfully"}


@router.get("/my/items", response_model=ItemListResponse)
async def get_my_items(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's items."""
    service = ItemService(db)
    filters = ItemFilter(owner_id=current_user.id, is_active=None)
    
    skip = (page - 1) * limit
    items, total = await service.get_all(skip, limit, filters)
    
    pages = (total + limit - 1) // limit
    
    return ItemListResponse(
        items=items,
        total=total,
        page=page,
        pages=pages,
        has_next=page < pages,
        has_prev=page > 1
    )
