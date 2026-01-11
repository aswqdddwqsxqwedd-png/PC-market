from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.models import CartItem, Item
from app.schemas import CartItemCreate, CartItemUpdate
from app.core.exceptions import NotFoundError, ValidationError


class CartService:
    """
    Service for shopping cart operations.
    
    Handles adding, updating, and removing items from user's cart.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize CartService.
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def get_cart(self, user_id: int) -> List[CartItem]:
        result = await self.db.execute(
            select(CartItem)
            .options(selectinload(CartItem.item).selectinload(Item.category))
            .where(CartItem.user_id == user_id)
            .order_by(CartItem.added_at.desc())
        )
        return list(result.scalars().all())
    
    async def get_cart_item(self, user_id: int, item_id: int) -> Optional[CartItem]:
        result = await self.db.execute(
            select(CartItem)
            .options(selectinload(CartItem.item))
            .where(CartItem.user_id == user_id, CartItem.item_id == item_id)
        )
        return result.scalar_one_or_none()
    
    async def add_to_cart(self, user_id: int, cart_data: CartItemCreate) -> CartItem:
        # Check if item exists
        item_result = await self.db.execute(
            select(Item).where(Item.id == cart_data.item_id, Item.is_active == True)
        )
        item = item_result.scalar_one_or_none()
        if not item:
            raise NotFoundError("Item", cart_data.item_id)
        
        # Check available quantity
        if item.quantity < cart_data.quantity:
            raise ValidationError(
                f"Not enough items in stock. Available: {item.quantity}",
                {"available": item.quantity, "requested": cart_data.quantity}
            )
        
        # Check if already in cart
        existing = await self.get_cart_item(user_id, cart_data.item_id)
        if existing:
            # Update quantity
            new_quantity = existing.quantity + cart_data.quantity
            if new_quantity > item.quantity:
                raise ValidationError(
                    f"Cannot add more items. Max available: {item.quantity}",
                    {"available": item.quantity, "in_cart": existing.quantity}
                )
            existing.quantity = new_quantity
            await self.db.flush()
            await self.db.refresh(existing)
            return existing
        
        # Create new cart item
        cart_item = CartItem(
            user_id=user_id,
            item_id=cart_data.item_id,
            quantity=cart_data.quantity
        )
        self.db.add(cart_item)
        await self.db.flush()
        await self.db.refresh(cart_item, ["item"])
        return cart_item
    
    async def update_quantity(
        self,
        user_id: int,
        item_id: int,
        cart_data: CartItemUpdate
    ) -> CartItem:
        cart_item = await self.get_cart_item(user_id, item_id)
        if not cart_item:
            raise NotFoundError("CartItem", item_id)
        
        # Check available quantity
        item_result = await self.db.execute(
            select(Item).where(Item.id == item_id)
        )
        item = item_result.scalar_one_or_none()
        if item and cart_data.quantity > item.quantity:
            raise ValidationError(
                f"Not enough items in stock. Available: {item.quantity}",
                {"available": item.quantity, "requested": cart_data.quantity}
            )
        
        cart_item.quantity = cart_data.quantity
        await self.db.flush()
        await self.db.refresh(cart_item)
        return cart_item
    
    async def remove_from_cart(self, user_id: int, item_id: int) -> bool:
        cart_item = await self.get_cart_item(user_id, item_id)
        if not cart_item:
            raise NotFoundError("CartItem", item_id)
        
        await self.db.delete(cart_item)
        await self.db.flush()
        return True
    
    async def clear_cart(self, user_id: int) -> bool:
        await self.db.execute(
            delete(CartItem).where(CartItem.user_id == user_id)
        )
        await self.db.flush()
        return True
    
    async def get_cart_total(self, user_id: int) -> tuple:
        """Returns (total_items, total_price)."""
        cart_items = await self.get_cart(user_id)
        total_items = sum(ci.quantity for ci in cart_items)
        total_price = sum(ci.quantity * ci.item.price for ci in cart_items)
        return total_items, total_price
