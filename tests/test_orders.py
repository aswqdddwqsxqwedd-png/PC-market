"""Tests for orders endpoints."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Category, Item, OrderStatus


@pytest.fixture
async def test_category(db_session: AsyncSession):
    """Create a test category."""
    category = Category(
        name="Процессоры",
        slug="processors",
        description="CPU"
    )
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    return category


@pytest.fixture
async def test_item(db_session: AsyncSession, test_seller, test_category):
    """Create a test item."""
    item = Item(
        name="Test Item",
        description="Test",
        price=1000.0,
        quantity=10,
        category_id=test_category.id,
        owner_id=test_seller.id
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    return item


@pytest.mark.asyncio
async def test_create_order_from_cart(client: AsyncClient, auth_headers, test_item):
    """Test creating order from cart."""
    # Add item to cart first
    await client.post(
        "/api/v1/cart/items",
        headers=auth_headers,
        json={
            "item_id": test_item.id,
            "quantity": 2
        }
    )
    
    # Create order
    response = await client.post(
        "/api/v1/orders",
        headers=auth_headers,
        json={"shipping_address": "Test Address"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == OrderStatus.PENDING.value
    assert data["total_price"] == test_item.price * 2
    assert len(data["items"]) == 1


@pytest.mark.asyncio
async def test_create_order_empty_cart(client: AsyncClient, auth_headers):
    """Test creating order with empty cart."""
    response = await client.post(
        "/api/v1/orders",
        headers=auth_headers,
        json={"shipping_address": "Test Address"}
    )
    # FastAPI returns 422 for validation errors, 400 for business logic errors
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_get_my_orders(client: AsyncClient, auth_headers, test_item):
    """Test getting user's orders."""
    # Create an order first
    await client.post(
        "/api/v1/cart/items",
        headers=auth_headers,
        json={"item_id": test_item.id, "quantity": 1}
    )
    await client.post(
        "/api/v1/orders",
        headers=auth_headers,
        json={"shipping_address": "Test"}
    )
    
    # Get orders
    response = await client.get("/api/v1/orders", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["orders"]) > 0


@pytest.mark.asyncio
async def test_get_order_by_id(client: AsyncClient, auth_headers, test_item):
    """Test getting order by ID."""
    # Create an order first
    await client.post(
        "/api/v1/cart/items",
        headers=auth_headers,
        json={"item_id": test_item.id, "quantity": 1}
    )
    create_response = await client.post(
        "/api/v1/orders",
        headers=auth_headers,
        json={"shipping_address": "Test"}
    )
    order_id = create_response.json()["id"]
    
    # Get order
    response = await client.get(f"/api/v1/orders/{order_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == order_id
    assert len(data["items"]) > 0


@pytest.mark.asyncio
async def test_update_order_status(client: AsyncClient, auth_headers, admin_headers, test_item):
    """Test updating order status."""
    import asyncio
    # Create an order as user
    await client.post(
        "/api/v1/cart/items",
        headers=auth_headers,
        json={"item_id": test_item.id, "quantity": 1}
    )
    # Create order directly - no sleep needed in tests
    create_response = await client.post(
        "/api/v1/orders",
        headers=auth_headers,
        json={"shipping_address": "Test"}
    )
    assert create_response is not None, "Failed to get response"
    assert create_response.status_code == 201, f"Failed to create order: {create_response.status_code} - {create_response.text[:200]}"
    order_data = create_response.json()
    order_id = order_data.get("id") or order_data.get("order_id")
    assert order_id is not None, f"Order ID not found in response: {order_data}"
    
    # Update status as admin
    response = await client.put(
        f"/api/v1/orders/{order_id}/status",
        headers=admin_headers,
        json={"status": OrderStatus.PAID.value}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == OrderStatus.PAID.value

