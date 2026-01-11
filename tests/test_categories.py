"""Tests for categories endpoints."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_get_categories(client: AsyncClient):
    """Test getting list of categories."""
    response = await client.get("/api/v1/categories")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_category_by_id(client: AsyncClient, db_session: AsyncSession):
    """Test getting category by ID."""
    from app.models import Category
    
    category = Category(
        name="Test Category",
        slug="test-category",
        description="Test"
    )
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    
    response = await client.get(f"/api/v1/categories/{category.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == category.id
    assert data["name"] == "Test Category"


@pytest.mark.asyncio
async def test_create_category_as_admin(client: AsyncClient, admin_headers):
    """Test creating category as admin."""
    response = await client.post(
        "/api/v1/admin/categories",
        headers=admin_headers,
        json={
            "name": "New Category",
            "slug": "new-category",
            "description": "New category description"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Category"


@pytest.mark.asyncio
async def test_create_category_as_user_forbidden(client: AsyncClient, auth_headers):
    """Test creating category as regular user (should fail)."""
    response = await client.post(
        "/api/v1/admin/categories",
        headers=auth_headers,
        json={
            "name": "New Category",
            "slug": "new-category",
            "description": "New category description"
        }
    )
    assert response.status_code == 403

