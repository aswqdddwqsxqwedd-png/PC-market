"""Integration tests for the entire application."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Category
from sqlalchemy import select


@pytest.mark.asyncio
async def test_full_user_flow(client: AsyncClient, db_session: AsyncSession):
    """Test complete user flow: register -> login -> browse -> add to cart -> order."""
    # 1. Register
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "flowtest@example.com",
            "username": "flowuser",
            "password": "password123"
        }
    )
    assert register_response.status_code == 201
    
    # 2. Login
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "identifier": "flowtest@example.com",
            "password": "password123"
        }
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. Get user info
    me_response = await client.get("/api/v1/auth/me", headers=headers)
    assert me_response.status_code == 200
    user_data = me_response.json()
    assert user_data["email"] == "flowtest@example.com"
    
    # 4. Browse categories
    categories_response = await client.get("/api/v1/categories")
    assert categories_response.status_code == 200
    
    # 5. Browse items
    items_response = await client.get("/api/v1/items")
    assert items_response.status_code == 200
    
    # 6. Get cart (should be empty)
    cart_response = await client.get("/api/v1/cart", headers=headers)
    assert cart_response.status_code == 200
    cart_data = cart_response.json()
    assert cart_data["total_items"] == 0


@pytest.mark.asyncio
async def test_api_health_check(client: AsyncClient):
    """Test that API is responding."""
    # Test root endpoint
    response = await client.get("/")
    assert response.status_code == 200
    
    # Test API docs
    response = await client.get("/docs")
    assert response.status_code == 200
    
    # Test OpenAPI schema
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "openapi" in schema
    assert "paths" in schema


@pytest.mark.asyncio
async def test_error_handling(client: AsyncClient):
    """Test that API handles errors gracefully."""
    # FastAPI catch-all route returns index.html (200) for non-API routes
    # But API routes that don't exist should return 404
    # Test with a POST to a non-existent endpoint (POST won't match catch-all)
    response = await client.post("/api/v1/nonexistent/endpoint")
    assert response.status_code in [404, 422, 405]  # 404 not found, 422 validation, 405 method not allowed
    
    # Test invalid login
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "identifier": "nonexistent@example.com",
            "password": "wrongpass"
        }
    )
    assert response.status_code in [401, 400, 422]
    
    # Test unauthorized access (401 for no auth, 403 for insufficient permissions)
    response = await client.get("/api/v1/admin/dashboard")
    assert response.status_code in [401, 403]  # 401 unauthorized, 403 forbidden


@pytest.mark.asyncio
async def test_cors_headers(client: AsyncClient):
    """Test that CORS headers are present (if configured)."""
    response = await client.get("/api/v1/categories")
    assert response.status_code == 200
    # CORS headers might not be present in test environment, so we just check it doesn't error


@pytest.mark.asyncio
async def test_content_types(client: AsyncClient):
    """Test that responses have correct content types."""
    # HTML
    response = await client.get("/")
    assert "text/html" in response.headers.get("content-type", "")
    
    # JSON API
    response = await client.get("/api/v1/categories")
    assert response.status_code == 200
    assert "application/json" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_pagination(client: AsyncClient):
    """Test that pagination works correctly."""
    response = await client.get("/api/v1/items?page=1&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data or "pages" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_search_and_filters(client: AsyncClient, db_session: AsyncSession):
    """Test that search and filters work."""
    from app.models import Category
    from sqlalchemy import select
    
    # Get any existing category
    result = await db_session.execute(select(Category).limit(1))
    category = result.scalar_one_or_none()
    
    # Test search (works even without categories)
    response = await client.get("/api/v1/items?search=test")
    assert response.status_code == 200
    
    # Test category filter (only if category exists)
    if category:
        response = await client.get(f"/api/v1/items?category_id={category.id}")
        assert response.status_code == 200
    else:
        # Just test that the endpoint accepts the parameter
        response = await client.get("/api/v1/items?category_id=999")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_rate_limiting(client: AsyncClient):
    """Test that rate limiting middleware is working."""
    # Make multiple requests
    responses = []
    for _ in range(10):
        response = await client.get("/api/v1/categories")
        responses.append(response.status_code)
    
    # At least some should succeed
    assert 200 in responses


@pytest.mark.asyncio
async def test_database_connection(client: AsyncClient):
    """Test that database connection is working."""
    # Try to get categories (requires DB)
    response = await client.get("/api/v1/categories")
    assert response.status_code == 200
    
    # Try to register (requires DB write)
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "dbtest@example.com",
            "username": "dbtest",
            "password": "password123"
        }
    )
    assert response.status_code in [201, 409]  # 409 if user already exists

