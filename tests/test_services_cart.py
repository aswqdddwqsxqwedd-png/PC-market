"""Tests for CartService."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.cart_service import CartService
from app.models import CartItem, Item, Category, User
from app.schemas import CartItemCreate, CartItemUpdate
from app.core.exceptions import NotFoundError, ValidationError


@pytest.mark.asyncio
async def test_get_cart_empty(db_session: AsyncSession, test_user):
    """Test getting empty cart."""
    service = CartService(db_session)
    cart = await service.get_cart(test_user.id)
    assert cart == []


@pytest.mark.asyncio
async def test_get_cart_item_not_found(db_session: AsyncSession, test_user, test_item):
    """Test getting non-existent cart item."""
    service = CartService(db_session)
    cart_item = await service.get_cart_item(test_user.id, test_item.id)
    assert cart_item is None


@pytest.mark.asyncio
async def test_add_to_cart_inactive_item(db_session: AsyncSession, test_user, test_category):
    """Test adding inactive item to cart."""
    item = Item(
        name="Inactive Item",
        description="Test",
        price=1000.0,
        quantity=10,
        category_id=test_category.id,
        owner_id=test_user.id,
        is_active=False
    )
    db_session.add(item)
    await db_session.flush()
    
    service = CartService(db_session)
    with pytest.raises(NotFoundError):
        await service.add_to_cart(test_user.id, CartItemCreate(item_id=item.id, quantity=1))


@pytest.mark.asyncio
async def test_add_to_cart_insufficient_quantity(db_session: AsyncSession, test_user, test_item):
    """Test adding item with insufficient quantity."""
    test_item.quantity = 5
    await db_session.flush()
    
    service = CartService(db_session)
    with pytest.raises(ValidationError):
        await service.add_to_cart(test_user.id, CartItemCreate(item_id=test_item.id, quantity=10))


@pytest.mark.asyncio
async def test_add_to_cart_existing_item(db_session: AsyncSession, test_user, test_item):
    """Test adding item that already exists in cart."""
    service = CartService(db_session)
    
    # Add item first time
    cart_item1 = await service.add_to_cart(test_user.id, CartItemCreate(item_id=test_item.id, quantity=2))
    assert cart_item1.quantity == 2
    
    # Add same item again
    cart_item2 = await service.add_to_cart(test_user.id, CartItemCreate(item_id=test_item.id, quantity=3))
    assert cart_item2.id == cart_item1.id
    assert cart_item2.quantity == 5


@pytest.mark.asyncio
async def test_add_to_cart_existing_item_exceeds_stock(db_session: AsyncSession, test_user, test_item):
    """Test adding existing item that would exceed stock."""
    test_item.quantity = 5
    await db_session.flush()
    
    service = CartService(db_session)
    
    # Add item first time
    await service.add_to_cart(test_user.id, CartItemCreate(item_id=test_item.id, quantity=3))
    
    # Try to add more than available
    with pytest.raises(ValidationError):
        await service.add_to_cart(test_user.id, CartItemCreate(item_id=test_item.id, quantity=3))


@pytest.mark.asyncio
async def test_update_quantity_not_found(db_session: AsyncSession, test_user, test_item):
    """Test updating quantity of non-existent cart item."""
    service = CartService(db_session)
    with pytest.raises(NotFoundError):
        await service.update_quantity(test_user.id, test_item.id, CartItemUpdate(quantity=5))


@pytest.mark.asyncio
async def test_update_quantity_insufficient_stock(db_session: AsyncSession, test_user, test_item):
    """Test updating quantity with insufficient stock."""
    test_item.quantity = 5
    await db_session.flush()
    
    service = CartService(db_session)
    await service.add_to_cart(test_user.id, CartItemCreate(item_id=test_item.id, quantity=2))
    
    with pytest.raises(ValidationError):
        await service.update_quantity(test_user.id, test_item.id, CartItemUpdate(quantity=10))


@pytest.mark.asyncio
async def test_remove_from_cart_not_found(db_session: AsyncSession, test_user, test_item):
    """Test removing non-existent cart item."""
    service = CartService(db_session)
    with pytest.raises(NotFoundError):
        await service.remove_from_cart(test_user.id, test_item.id)


@pytest.mark.asyncio
async def test_clear_cart(db_session: AsyncSession, test_user, test_item):
    """Test clearing cart."""
    service = CartService(db_session)
    await service.add_to_cart(test_user.id, CartItemCreate(item_id=test_item.id, quantity=2))
    
    result = await service.clear_cart(test_user.id)
    assert result is True
    
    cart = await service.get_cart(test_user.id)
    assert len(cart) == 0


@pytest.mark.asyncio
async def test_get_cart_total(db_session: AsyncSession, test_user, test_category):
    """Test getting cart total."""
    item1 = Item(
        name="Item 1",
        description="Test",
        price=1000.0,
        quantity=10,
        category_id=test_category.id,
        owner_id=test_user.id
    )
    item2 = Item(
        name="Item 2",
        description="Test",
        price=2000.0,
        quantity=10,
        category_id=test_category.id,
        owner_id=test_user.id
    )
    db_session.add(item1)
    db_session.add(item2)
    await db_session.flush()
    
    service = CartService(db_session)
    await service.add_to_cart(test_user.id, CartItemCreate(item_id=item1.id, quantity=2))
    await service.add_to_cart(test_user.id, CartItemCreate(item_id=item2.id, quantity=3))
    
    total_items, total_price = await service.get_cart_total(test_user.id)
    assert total_items == 5
    assert total_price == 1000.0 * 2 + 2000.0 * 3

