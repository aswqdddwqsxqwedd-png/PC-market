from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple
from app.models import Item, Category, User
from app.schemas import ItemCreate, ItemUpdate, ItemFilter
from app.core.exceptions import NotFoundError, AuthorizationError


class ItemService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, item_id: int) -> Optional[Item]:
        result = await self.db.execute(
            select(Item)
            .options(selectinload(Item.category), selectinload(Item.owner))
            .where(Item.id == item_id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 20,
        filters: Optional[ItemFilter] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Tuple[List[Item], int]:
        query = select(Item).options(selectinload(Item.category), selectinload(Item.owner))
        count_query = select(func.count(Item.id))
        
        # Apply filters
        if filters:
            if filters.category_id:
                query = query.where(Item.category_id == filters.category_id)
                count_query = count_query.where(Item.category_id == filters.category_id)
            if filters.min_price is not None:
                query = query.where(Item.price >= filters.min_price)
                count_query = count_query.where(Item.price >= filters.min_price)
            if filters.max_price is not None:
                query = query.where(Item.price <= filters.max_price)
                count_query = count_query.where(Item.price <= filters.max_price)
            if filters.search:
                search_term = f"%{filters.search}%"
                query = query.where(
                    or_(
                        Item.name.ilike(search_term),
                        Item.description.ilike(search_term)
                    )
                )
                count_query = count_query.where(
                    or_(
                        Item.name.ilike(search_term),
                        Item.description.ilike(search_term)
                    )
                )
            if filters.owner_id:
                query = query.where(Item.owner_id == filters.owner_id)
                count_query = count_query.where(Item.owner_id == filters.owner_id)
            if filters.is_active is not None:
                query = query.where(Item.is_active == filters.is_active)
                count_query = count_query.where(Item.is_active == filters.is_active)
        
        # Count total
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Apply sorting
        sort_column = getattr(Item, sort_by, Item.created_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        items = list(result.scalars().all())
        
        return items, total
    
    async def count(self, is_active: Optional[bool] = None) -> int:
        query = select(func.count(Item.id))
        if is_active is not None:
            query = query.where(Item.is_active == is_active)
        result = await self.db.execute(query)
        return result.scalar()
    
    async def create(self, item_data: ItemCreate, owner_id: int) -> Item:
        item = Item(
            name=item_data.name,
            description=item_data.description,
            price=item_data.price,
            quantity=item_data.quantity,
            image_url=item_data.image_url,
            category_id=item_data.category_id,
            owner_id=owner_id
        )
        self.db.add(item)
        await self.db.flush()
        await self.db.refresh(item)
        
        # Load relationships
        await self.db.refresh(item, ["category", "owner"])
        return item
    
    async def update(
        self,
        item_id: int,
        item_data: ItemUpdate,
        user_id: int,
        is_admin: bool = False
    ) -> Item:
        item = await self.get_by_id(item_id)
        if not item:
            raise NotFoundError("Item", item_id)
        
        # Check ownership
        if not is_admin and item.owner_id != user_id:
            raise AuthorizationError("You don't have permission to update this item")
        
        update_data = item_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(item, key, value)
        
        await self.db.flush()
        await self.db.refresh(item)
        return item
    
    async def delete(self, item_id: int, user_id: int, is_admin: bool = False) -> bool:
        item = await self.get_by_id(item_id)
        if not item:
            raise NotFoundError("Item", item_id)
        
        # Check ownership
        if not is_admin and item.owner_id != user_id:
            raise AuthorizationError("You don't have permission to delete this item")
        
        await self.db.delete(item)
        await self.db.flush()
        return True
    
    async def get_by_category(self, category_id: int, limit: int = 10) -> List[Item]:
        result = await self.db.execute(
            select(Item)
            .where(Item.category_id == category_id, Item.is_active == True)
            .order_by(Item.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_stats_by_category(self) -> dict:
        result = await self.db.execute(
            select(
                Category.name,
                func.count(Item.id).label('count')
            )
            .join(Item, Item.category_id == Category.id)
            .group_by(Category.id)
        )
        return {row.name: row.count for row in result}
