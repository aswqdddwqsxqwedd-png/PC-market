"""Tests for admin endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_dashboard_stats(client: AsyncClient, admin_headers):
    """Test getting dashboard statistics."""
    response = await client.get("/api/v1/admin/dashboard", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_users" in data
    assert "total_items" in data
    assert "total_orders" in data


@pytest.mark.asyncio
async def test_get_all_users(client: AsyncClient, admin_headers):
    """Test getting all users."""
    response = await client.get("/api/v1/admin/users", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_all_items(client: AsyncClient, admin_headers):
    """Test getting all items."""
    response = await client.get("/api/v1/admin/items", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_get_all_orders(client: AsyncClient, admin_headers):
    """Test getting all orders."""
    response = await client.get("/api/v1/admin/orders", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "orders" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_admin_access_required(client: AsyncClient, auth_headers):
    """Test that admin endpoints require admin role."""
    response = await client.get("/api/v1/admin/dashboard", headers=auth_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_users_stats(client: AsyncClient, admin_headers):
    """Test getting users statistics."""
    response = await client.get("/api/v1/admin/users/stats", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "active" in data
    assert "by_role" in data


@pytest.mark.asyncio
async def test_get_user_by_id(client: AsyncClient, admin_headers, test_user):
    """Test getting user by ID."""
    response = await client.get(f"/api/v1/admin/users/{test_user.id}", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user.id


@pytest.mark.asyncio
async def test_get_user_not_found(client: AsyncClient, admin_headers):
    """Test getting non-existent user."""
    response = await client.get("/api/v1/admin/users/99999", headers=admin_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_user(client: AsyncClient, admin_headers, test_user):
    """Test updating user."""
    response = await client.put(
        f"/api/v1/admin/users/{test_user.id}",
        headers=admin_headers,
        json={"is_active": False}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_delete_user(client: AsyncClient, admin_headers, test_user):
    """Test deleting user."""
    response = await client.delete(f"/api/v1/admin/users/{test_user.id}", headers=admin_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_delete_self_forbidden(client: AsyncClient, admin_headers, test_admin):
    """Test that admin cannot delete themselves."""
    response = await client.delete(f"/api/v1/admin/users/{test_admin.id}", headers=admin_headers)
    assert response.status_code in [400, 422]  # ValidationError returns 422


@pytest.mark.asyncio
async def test_get_items_stats(client: AsyncClient, admin_headers):
    """Test getting items statistics."""
    response = await client.get("/api/v1/admin/items/stats", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "active" in data


@pytest.mark.asyncio
async def test_get_reports_users(client: AsyncClient, admin_headers):
    """Test getting users report."""
    response = await client.get("/api/v1/admin/reports/users", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_users" in data or "new_users" in data


@pytest.mark.asyncio
async def test_get_reports_items(client: AsyncClient, admin_headers):
    """Test getting items report."""
    response = await client.get("/api/v1/admin/reports/items", headers=admin_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_reports_categories(client: AsyncClient, admin_headers):
    """Test getting categories report."""
    response = await client.get("/api/v1/admin/reports/categories", headers=admin_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_reports_sales(client: AsyncClient, admin_headers):
    """Test getting sales report."""
    response = await client.get("/api/v1/admin/reports/sales", headers=admin_headers)
    assert response.status_code == 200

