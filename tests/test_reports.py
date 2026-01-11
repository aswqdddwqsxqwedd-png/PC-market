"""Tests for admin reports endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_users_report(client: AsyncClient, admin_headers):
    """Test getting users report."""
    response = await client.get(
        "/api/v1/admin/reports/users",
        headers=admin_headers,
        params={"days": 30}
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_users" in data
    assert "new_users" in data
    assert "active_users" in data


@pytest.mark.asyncio
async def test_get_items_report(client: AsyncClient, admin_headers):
    """Test getting items report."""
    response = await client.get(
        "/api/v1/admin/reports/items",
        headers=admin_headers,
        params={"days": 30}
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_items" in data
    assert "total_revenue" in data
    assert "top_selling_items" in data


@pytest.mark.asyncio
async def test_get_categories_report(client: AsyncClient, admin_headers):
    """Test getting categories report."""
    response = await client.get(
        "/api/v1/admin/reports/categories",
        headers=admin_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_categories" in data
    assert "categories" in data
    assert "popular_categories" in data
    assert "top_revenue_categories" in data


@pytest.mark.asyncio
async def test_get_sales_report(client: AsyncClient, admin_headers):
    """Test getting sales report."""
    response = await client.get(
        "/api/v1/admin/reports/sales",
        headers=admin_headers,
        params={"days": 30}
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_revenue" in data
    assert "total_orders" in data
    assert "orders_by_status" in data
    assert "average_order_value" in data


@pytest.mark.asyncio
async def test_reports_require_admin(client: AsyncClient, auth_headers):
    """Test that reports require admin access."""
    response = await client.get(
        "/api/v1/admin/reports/users",
        headers=auth_headers
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_users_report_with_role_filter(client: AsyncClient, admin_headers):
    """Test getting users report with role filter."""
    response = await client.get(
        "/api/v1/admin/reports/users",
        headers=admin_headers,
        params={"days": 30, "role": "user"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_users" in data

