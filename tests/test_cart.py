"""Tests for cart endpoints."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Category, Item


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
async def test_get_cart_empty(client: AsyncClient, auth_headers):
    """Test getting empty cart."""
    response = await client.get("/api/v1/cart", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total_price"] == 0.0
    assert data["total_items"] == 0


@pytest.mark.asyncio
async def test_add_item_to_cart(client: AsyncClient, auth_headers, test_item):
    """Test adding item to cart."""
    response = await client.post(
        "/api/v1/cart/items",
        headers=auth_headers,
        json={
            "item_id": test_item.id,
            "quantity": 2
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["item_id"] == test_item.id
    assert data["quantity"] == 2


@pytest.mark.asyncio
async def test_get_cart_with_items(client: AsyncClient, auth_headers, test_item):
    """Test getting cart with items."""
    # Add item first
    await client.post(
        "/api/v1/cart/items",
        headers=auth_headers,
        json={
            "item_id": test_item.id,
            "quantity": 2
        }
    )
    
    # Get cart
    response = await client.get("/api/v1/cart", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["total_price"] == test_item.price * 2
    assert data["total_items"] == 2


@pytest.mark.asyncio
async def test_update_cart_item_quantity(client: AsyncClient, auth_headers, test_item):
    """Test updating cart item quantity."""
    # Add item first
    add_response = await client.post(
        "/api/v1/cart/items",
        headers=auth_headers,
        json={
            "item_id": test_item.id,
            "quantity": 1
        }
    )
    cart_item_id = add_response.json()["id"]
    
    # Update quantity
    response = await client.put(
        f"/api/v1/cart/items/{cart_item_id}",
        headers=auth_headers,
        json={"quantity": 5}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["quantity"] == 5


@pytest.mark.asyncio
async def test_delete_cart_item(client: AsyncClient, auth_headers, test_item):
    """Test deleting item from cart."""
    # Add item first
    add_response = await client.post(
        "/api/v1/cart/items",
        headers=auth_headers,
        json={
            "item_id": test_item.id,
            "quantity": 1
        }
    )
    cart_item_id = add_response.json()["id"]
    
    # Delete item
    response = await client.delete(
        f"/api/v1/cart/items/{cart_item_id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    
    # Verify cart is empty
    cart_response = await client.get("/api/v1/cart", headers=auth_headers)
    assert len(cart_response.json()["items"]) == 0

