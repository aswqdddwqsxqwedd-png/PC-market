from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
import re
from app.models import Category, Item
from app.schemas import CategoryCreate, CategoryUpdate
from app.core.exceptions import NotFoundError, ConflictError


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text


class CategoryService:
    """
    Service for category management operations.
    
    Handles CRUD operations for product categories.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize CategoryService.
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def get_by_id(self, category_id: int) -> Optional[Category]:
        result = await self.db.execute(select(Category).where(Category.id == category_id))
        return result.scalar_one_or_none()
    
    async def get_by_slug(self, slug: str) -> Optional[Category]:
        result = await self.db.execute(select(Category).where(Category.slug == slug))
        return result.scalar_one_or_none()
    
    async def get_all(self) -> List[Category]:
        result = await self.db.execute(select(Category).order_by(Category.name))
        return list(result.scalars().all())
    
    async def get_with_counts(self) -> List[dict]:
        """Get categories with item counts."""
        query = select(
            Category,
            func.count(Item.id).label('items_count')
        ).outerjoin(Item, Item.category_id == Category.id).group_by(Category.id)
        
        result = await self.db.execute(query)
        categories = []
        for row in result:
            cat_dict = {
                "id": row.Category.id,
                "name": row.Category.name,
                "slug": row.Category.slug,
                "description": row.Category.description,
                "icon": row.Category.icon,
                "created_at": row.Category.created_at,
                "items_count": row.items_count
            }
            categories.append(cat_dict)
        return categories
    
    async def count(self) -> int:
        result = await self.db.execute(select(func.count(Category.id)))
        return result.scalar()
    
    async def create(self, category_data: CategoryCreate) -> Category:
        # Generate slug if not provided
        slug = category_data.slug or slugify(category_data.name)
        
        # Check for existing slug
        existing = await self.get_by_slug(slug)
        if existing:
            raise ConflictError("Category", f"Category with slug '{slug}' already exists")
        
        category = Category(
            name=category_data.name,
            slug=slug,
            description=category_data.description,
            icon=category_data.icon
        )
        self.db.add(category)
        await self.db.flush()
        await self.db.refresh(category)
        return category
    
    async def update(self, category_id: int, category_data: CategoryUpdate) -> Category:
        category = await self.get_by_id(category_id)
        if not category:
            raise NotFoundError("Category", category_id)
        
        update_data = category_data.model_dump(exclude_unset=True)
        
        # Update slug if name is changed and slug not provided
        if 'name' in update_data and 'slug' not in update_data:
            update_data['slug'] = slugify(update_data['name'])
        
        for key, value in update_data.items():
            setattr(category, key, value)
        
        await self.db.flush()
        await self.db.refresh(category)
        return category
    
    async def delete(self, category_id: int) -> bool:
        category = await self.get_by_id(category_id)
        if not category:
            raise NotFoundError("Category", category_id)
        
        await self.db.delete(category)
        await self.db.flush()
        return True
