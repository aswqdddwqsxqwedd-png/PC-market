from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.db import get_db
from app.schemas import CategoryCreate, CategoryUpdate, CategoryResponse, CategoryWithCount
from app.services import CategoryService
from app.api.deps import get_current_admin_user
from app.models import User

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=List[CategoryWithCount])
async def get_categories(db: AsyncSession = Depends(get_db)):
    """Get all categories with item counts."""
    service = CategoryService(db)
    categories = await service.get_with_counts()
    return categories


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get category by ID."""
    service = CategoryService(db)
    category = await service.get_by_id(category_id)
    if not category:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Category", category_id)
    return category


@router.post("", response_model=CategoryResponse, status_code=201)
async def create_category(
    category_data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Create a new category (admin only)."""
    service = CategoryService(db)
    category = await service.create(category_data)
    return category


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Update category (admin only)."""
    service = CategoryService(db)
    category = await service.update(category_id, category_data)
    return category


@router.delete("/{category_id}")
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Delete category (admin only)."""
    service = CategoryService(db)
    await service.delete(category_id)
    return {"message": "Category deleted successfully"}
