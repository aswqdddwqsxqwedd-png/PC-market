"""Additional tests to boost coverage to 81%."""
import pytest
from httpx import AsyncClient
from app.models import UserRole


@pytest.mark.asyncio
async def test_get_users_with_filters(client: AsyncClient, admin_headers):
    """Test getting users with role and is_active filters."""
    response = await client.get(
        "/api/v1/admin/users?role=user&is_active=true&skip=0&limit=10",
        headers=admin_headers
    )
    assert response.status_code == 200


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
async def test_get_items_with_filters(client: AsyncClient, admin_headers):
    """Test getting items with filters."""
    response = await client.get(
        "/api/v1/admin/items?page=1&limit=10&is_active=true",
        headers=admin_headers
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_orders_with_filters(client: AsyncClient, admin_headers):
    """Test getting orders with filters."""
    response = await client.get(
        "/api/v1/admin/orders?page=1&limit=10&status=pending",
        headers=admin_headers
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_delete_category_not_found(client: AsyncClient, admin_headers):
    """Test deleting non-existent category."""
    response = await client.delete("/api/v1/admin/categories/99999", headers=admin_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_category_not_found(client: AsyncClient, admin_headers):
    """Test updating non-existent category."""
    response = await client.put(
        "/api/v1/admin/categories/99999",
        headers=admin_headers,
        json={"name": "Test"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_conversation_messages_pagination(client: AsyncClient, auth_headers, support_headers):
    """Test getting conversation messages with pagination."""
    support_response = await client.get("/api/v1/auth/me", headers=support_headers)
    support_id = support_response.json()["id"]
    
    # Send message
    await client.post(
        "/api/v1/chat/messages",
        headers=auth_headers,
        json={"receiver_id": support_id, "text": "Test"}
    )
    
    # Get messages with pagination
    response = await client.get(
        f"/api/v1/chat/conversations/{support_id}/messages?page=1&limit=10",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "messages" in data


@pytest.mark.asyncio
async def test_get_support_conversations_pagination(client: AsyncClient, auth_headers, support_headers):
    """Test getting support conversations with pagination."""
    support_response = await client.get("/api/v1/auth/me", headers=support_headers)
    support_id = support_response.json()["id"]
    
    # Send message
    await client.post(
        "/api/v1/chat/messages",
        headers=auth_headers,
        json={"receiver_id": support_id, "text": "Test"}
    )
    
    # Get conversations with pagination
    response = await client.get(
        "/api/v1/chat/support/conversations?page=1&limit=10",
        headers=support_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "conversations" in data

