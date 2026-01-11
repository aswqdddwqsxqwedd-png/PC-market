"""Tests for OrderService."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.order_service import OrderService
from app.models import Order, OrderItem, OrderStatus, CartItem, Item, User
from app.schemas import OrderCreate, OrderStatusUpdate
from app.core.exceptions import NotFoundError, ValidationError, AuthorizationError


@pytest.mark.asyncio
async def test_get_by_id_not_found(db_session: AsyncSession):
    """Test getting non-existent order."""
    service = OrderService(db_session)
    order = await service.get_by_id(999)
    assert order is None


@pytest.mark.asyncio
async def test_get_user_orders_with_status(db_session: AsyncSession, test_user):
    """Test getting user orders with status filter."""
    order1 = Order(
        user_id=test_user.id,
        total_price=1000.0,
        status=OrderStatus.PENDING,
        shipping_address="Test"
    )
    order2 = Order(
        user_id=test_user.id,
        total_price=2000.0,
        status=OrderStatus.PAID,
        shipping_address="Test"
    )
    db_session.add(order1)
    db_session.add(order2)
    await db_session.flush()
    
    service = OrderService(db_session)
    orders, total = await service.get_user_orders(test_user.id, status=OrderStatus.PENDING)
    assert total >= 1
    assert all(order.status == OrderStatus.PENDING for order in orders)


@pytest.mark.asyncio
async def test_get_all_orders_with_status(db_session: AsyncSession, test_user):
    """Test getting all orders with status filter."""
    order = Order(
        user_id=test_user.id,
        total_price=1000.0,
        status=OrderStatus.PENDING,
        shipping_address="Test"
    )
    db_session.add(order)
    await db_session.flush()
    
    service = OrderService(db_session)
    orders, total = await service.get_all_orders(status=OrderStatus.PENDING)
    assert total >= 1
    assert all(order.status == OrderStatus.PENDING for order in orders)


@pytest.mark.asyncio
async def test_create_from_cart_empty(db_session: AsyncSession, test_user):
    """Test creating order from empty cart."""
    service = OrderService(db_session)
    with pytest.raises(ValidationError, match="Корзина пуста"):
        await service.create_from_cart(test_user.id, OrderCreate(shipping_address="Test"))


@pytest.mark.asyncio
async def test_create_from_cart_insufficient_stock(db_session: AsyncSession, test_user, test_category):
    """Test creating order with insufficient stock."""
    item = Item(
        name="Test Item",
        description="Test",
        price=1000.0,
        quantity=5,
        category_id=test_category.id,
        owner_id=test_user.id
    )
    db_session.add(item)
    await db_session.flush()
    
    cart_item = CartItem(
        user_id=test_user.id,
        item_id=item.id,
        quantity=10
    )
    db_session.add(cart_item)
    await db_session.flush()
    
    service = OrderService(db_session)
    with pytest.raises(ValidationError):
        await service.create_from_cart(test_user.id, OrderCreate(shipping_address="Test"))


@pytest.mark.asyncio
async def test_update_status_not_found(db_session: AsyncSession, test_user):
    """Test updating status of non-existent order."""
    service = OrderService(db_session)
    with pytest.raises(NotFoundError):
        await service.update_status(
            999,
            OrderStatusUpdate(status=OrderStatus.PAID),
            test_user.id,
            test_user.role
        )


@pytest.mark.asyncio
async def test_update_status_unauthorized(db_session: AsyncSession, test_user, test_seller):
    """Test updating order by non-owner."""
    order = Order(
        user_id=test_user.id,
        total_price=1000.0,
        status=OrderStatus.PENDING,
        shipping_address="Test"
    )
    db_session.add(order)
    await db_session.flush()
    
    service = OrderService(db_session)
    with pytest.raises(AuthorizationError):
        await service.update_status(
            order.id,
            OrderStatusUpdate(status=OrderStatus.PAID),
            test_seller.id,
            test_seller.role
        )


@pytest.mark.asyncio
async def test_update_status_invalid_transition(db_session: AsyncSession, test_user):
    """Test updating order with invalid status transition."""
    order = Order(
        user_id=test_user.id,
        total_price=1000.0,
        status=OrderStatus.PENDING,
        shipping_address="Test"
    )
    db_session.add(order)
    await db_session.flush()
    
    service = OrderService(db_session)
    with pytest.raises(ValidationError):
        await service.update_status(
            order.id,
            OrderStatusUpdate(status=OrderStatus.DELIVERED),  # Invalid: PENDING -> DELIVERED
            test_user.id,
            test_user.role
        )


@pytest.mark.asyncio
async def test_count_with_status(db_session: AsyncSession, test_user):
    """Test counting orders with status."""
    order = Order(
        user_id=test_user.id,
        total_price=1000.0,
        status=OrderStatus.PENDING,
        shipping_address="Test"
    )
    db_session.add(order)
    await db_session.flush()
    
    service = OrderService(db_session)
    total = await service.count()
    pending = await service.count(status=OrderStatus.PENDING)
    
    assert total >= 1
    assert pending >= 1


@pytest.mark.asyncio
async def test_get_total_revenue(db_session: AsyncSession, test_user):
    """Test getting total revenue."""
    order1 = Order(
        user_id=test_user.id,
        total_price=1000.0,
        status=OrderStatus.PAID,
        shipping_address="Test"
    )
    order2 = Order(
        user_id=test_user.id,
        total_price=2000.0,
        status=OrderStatus.DELIVERED,
        shipping_address="Test"
    )
    order3 = Order(
        user_id=test_user.id,
        total_price=500.0,
        status=OrderStatus.PENDING,
        shipping_address="Test"
    )
    db_session.add(order1)
    db_session.add(order2)
    db_session.add(order3)
    await db_session.flush()
    
    service = OrderService(db_session)
    revenue = await service.get_total_revenue()
    assert revenue >= 3000.0  # Only PAID, SHIPPED, DELIVERED count


@pytest.mark.asyncio
async def test_get_stats_by_status(db_session: AsyncSession, test_user):
    """Test getting stats by status."""
    order1 = Order(
        user_id=test_user.id,
        total_price=1000.0,
        status=OrderStatus.PENDING,
        shipping_address="Test"
    )
    order2 = Order(
        user_id=test_user.id,
        total_price=2000.0,
        status=OrderStatus.PAID,
        shipping_address="Test"
    )
    db_session.add(order1)
    db_session.add(order2)
    await db_session.flush()
    
    service = OrderService(db_session)
    stats = await service.get_stats_by_status()
    assert isinstance(stats, dict)
    assert OrderStatus.PENDING.value in stats or OrderStatus.PAID.value in stats


@pytest.mark.asyncio
async def test_delete_not_admin(db_session: AsyncSession, test_user):
    """Test deleting order by non-admin."""
    order = Order(
        user_id=test_user.id,
        total_price=1000.0,
        status=OrderStatus.PENDING,
        shipping_address="Test"
    )
    db_session.add(order)
    await db_session.flush()
    
    service = OrderService(db_session)
    with pytest.raises(AuthorizationError):
        await service.delete(order.id, is_admin=False)


@pytest.mark.asyncio
async def test_delete_by_admin(db_session: AsyncSession, test_user, test_admin):
    """Test deleting order by admin."""
    order = Order(
        user_id=test_user.id,
        total_price=1000.0,
        status=OrderStatus.PENDING,
        shipping_address="Test"
    )
    db_session.add(order)
    await db_session.flush()
    
    service = OrderService(db_session)
    result = await service.delete(order.id, is_admin=True)
    assert result is True
    
    found = await service.get_by_id(order.id)
    assert found is None

