"""Quick tests for admin endpoints to boost coverage."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_users_with_pagination(client: AsyncClient, admin_headers):
    """Test getting users with pagination."""
    response = await client.get(
        "/api/v1/admin/users?page=1&limit=10",
        headers=admin_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_items_with_pagination(client: AsyncClient, admin_headers):
    """Test getting items with pagination."""
    response = await client.get(
        "/api/v1/admin/items?page=1&limit=10",
        headers=admin_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_get_orders_with_pagination(client: AsyncClient, admin_headers):
    """Test getting orders with pagination."""
    response = await client.get(
        "/api/v1/admin/orders?page=1&limit=10",
        headers=admin_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "orders" in data
    assert "total" in data

