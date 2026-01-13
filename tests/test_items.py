"""Tests for items endpoints."""
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
        description="CPU для настольных ПК"
    )
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    return category


@pytest.fixture
async def test_item(db_session: AsyncSession, test_seller, test_category):
    """Create a test item."""
    item = Item(
        name="Test CPU",
        description="Test processor",
        price=10000.0,
        quantity=10,
        category_id=test_category.id,
        owner_id=test_seller.id,
        image_url="https://example.com/image.jpg"
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    return item


@pytest.mark.asyncio
async def test_get_items(client: AsyncClient, test_item):
    """Test getting list of items."""
    response = await client.get("/api/v1/items")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert len(data["items"]) > 0


@pytest.mark.asyncio
async def test_get_item_by_id(client: AsyncClient, test_item):
    """Test getting item by ID."""
    response = await client.get(f"/api/v1/items/{test_item.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_item.id
    assert data["name"] == test_item.name


@pytest.mark.asyncio
async def test_get_item_not_found(client: AsyncClient):
    """Test getting non-existent item."""
    response = await client.get("/api/v1/items/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_item_as_seller(client: AsyncClient, seller_headers, test_category):
    """Test creating item as seller."""
    response = await client.post(
        "/api/v1/items",
        headers=seller_headers,
        json={
            "name": "New Item",
            "description": "New item description",
            "price": 5000.0,
            "quantity": 5,
            "category_id": test_category.id,
            "image_url": "https://example.com/new.jpg"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Item"
    assert data["price"] == 5000.0


@pytest.mark.asyncio
async def test_create_item_as_user_forbidden(client: AsyncClient, auth_headers, test_category):
    """Test creating item as regular user (should fail)."""
    response = await client.post(
        "/api/v1/items",
        headers=auth_headers,
        json={
            "name": "New Item",
            "description": "New item description",
            "price": 5000.0,
            "quantity": 5,
            "category_id": test_category.id
        }
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_item_as_owner(client: AsyncClient, seller_headers, test_item):
    """Test updating item as owner."""
    response = await client.put(
        f"/api/v1/items/{test_item.id}",
        headers=seller_headers,
        json={
            "name": "Updated Item",
            "price": 15000.0
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Item"
    assert data["price"] == 15000.0


@pytest.mark.asyncio
async def test_delete_item_as_owner(client: AsyncClient, seller_headers, test_item):
    """Test deleting item as owner."""
    response = await client.delete(
        f"/api/v1/items/{test_item.id}",
        headers=seller_headers
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_filter_items_by_category(client: AsyncClient, test_item, test_category):
    """Test filtering items by category."""
    response = await client.get(f"/api/v1/items?category_id={test_category.id}")
    assert response.status_code == 200
    data = response.json()
    assert all(item["category_id"] == test_category.id for item in data["items"])


@pytest.mark.asyncio
async def test_filter_items_by_price(client: AsyncClient, test_item):
    """Test filtering items by price range."""
    response = await client.get("/api/v1/items?min_price=5000&max_price=15000")
    assert response.status_code == 200
    data = response.json()
    assert all(5000 <= item["price"] <= 15000 for item in data["items"])

