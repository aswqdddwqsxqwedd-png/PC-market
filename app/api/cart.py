from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.schemas import CartItemCreate, CartItemUpdate, CartItemResponse, CartResponse
from app.services import CartService
from app.api.deps import get_current_user
from app.models import User

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.get("", response_model=CartResponse)
async def get_cart(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's cart."""
    service = CartService(db)
    cart_items = await service.get_cart(current_user.id)
    total_items, total_price = await service.get_cart_total(current_user.id)
    
    return CartResponse(
        items=cart_items,
        total_items=total_items,
        total_price=total_price
    )


@router.post("/items", response_model=CartItemResponse, status_code=201)
async def add_to_cart(
    cart_data: CartItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add item to cart."""
    service = CartService(db)
    cart_item = await service.add_to_cart(current_user.id, cart_data)
    return cart_item


@router.put("/items/{item_id}", response_model=CartItemResponse)
async def update_cart_item(
    item_id: int,
    cart_data: CartItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update cart item quantity."""
    service = CartService(db)
    cart_item = await service.update_quantity(current_user.id, item_id, cart_data)
    return cart_item


@router.delete("/items/{item_id}")
async def remove_from_cart(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove item from cart."""
    service = CartService(db)
    await service.remove_from_cart(current_user.id, item_id)
    return {"message": "Item removed from cart"}


@router.delete("")
async def clear_cart(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Clear all items from cart."""
    service = CartService(db)
    await service.clear_cart(current_user.id)
    return {"message": "Cart cleared"}
