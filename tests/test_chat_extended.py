"""Extended tests for chat endpoints to increase coverage."""
import pytest
from httpx import AsyncClient
from app.models import UserRole, OrderStatus


@pytest.mark.asyncio
async def test_mark_message_as_read(client: AsyncClient, auth_headers, support_headers):
    """Test marking message as read."""
    # Get users
    me_response = await client.get("/api/v1/auth/me", headers=auth_headers)
    user_id = me_response.json()["id"]
    
    support_response = await client.get("/api/v1/auth/me", headers=support_headers)
    support_id = support_response.json()["id"]
    
    # Send message
    msg_response = await client.post(
        "/api/v1/chat/messages",
        headers=auth_headers,
        json={
            "receiver_id": support_id,
            "text": "Test message"
        }
    )
    message_id = msg_response.json()["id"]
    
    # Mark as read
    response = await client.post(
        f"/api/v1/chat/messages/{message_id}/read",
        headers=support_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert data["count"] >= 1


@pytest.mark.asyncio
async def test_connect_to_support(client: AsyncClient, auth_headers, test_support):
    """Test connecting to support."""
    response = await client.post(
        "/api/v1/chat/support/connect",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "support_user_id" in data
    assert "support_username" in data
    assert data["support_user_id"] == test_support.id


@pytest.mark.asyncio
async def test_get_support_conversations(client: AsyncClient, auth_headers, support_headers):
    """Test getting support conversations."""
    # Send message to support first
    support_response = await client.get("/api/v1/auth/me", headers=support_headers)
    support_id = support_response.json()["id"]
    
    await client.post(
        "/api/v1/chat/messages",
        headers=auth_headers,
        json={
            "receiver_id": support_id,
            "text": "Support message"
        }
    )
    
    # Get support conversations
    response = await client.get(
        "/api/v1/chat/support/conversations",
        headers=support_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "conversations" in data
    assert isinstance(data["conversations"], list)


@pytest.mark.asyncio
async def test_get_support_status(client: AsyncClient, support_headers):
    """Test getting support status."""
    response = await client.get("/api/v1/chat/support/status", headers=support_headers)
    assert response.status_code == 200
    data = response.json()
    assert "is_online" in data
    assert "online_support_count" in data


@pytest.mark.asyncio
async def test_resolve_conversation(client: AsyncClient, auth_headers, support_headers):
    """Test resolving conversation."""
    # Get users
    me_response = await client.get("/api/v1/auth/me", headers=auth_headers)
    user_id = me_response.json()["id"]
    
    support_response = await client.get("/api/v1/auth/me", headers=support_headers)
    support_id = support_response.json()["id"]
    
    # Send messages
    await client.post(
        "/api/v1/chat/messages",
        headers=auth_headers,
        json={
            "receiver_id": support_id,
            "text": "Message 1"
        }
    )
    
    # Resolve conversation
    response = await client.post(
        f"/api/v1/chat/conversations/{user_id}/resolve",
        headers=support_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "resolved_count" in data  # API returns "resolved_count", not "count"
    assert data["resolved_count"] >= 1


@pytest.mark.asyncio
async def test_delete_conversation(client: AsyncClient, auth_headers, support_headers):
    """Test deleting conversation."""
    # Get users
    me_response = await client.get("/api/v1/auth/me", headers=auth_headers)
    user_id = me_response.json()["id"]
    
    support_response = await client.get("/api/v1/auth/me", headers=support_headers)
    support_id = support_response.json()["id"]
    
    # Send messages
    await client.post(
        "/api/v1/chat/messages",
        headers=auth_headers,
        json={
            "receiver_id": support_id,
            "text": "Message to delete"
        }
    )
    
    # Delete conversation
    response = await client.delete(
        f"/api/v1/chat/conversations/{user_id}",
        headers=support_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "deleted_count" in data  # API returns "deleted_count", not "count"
    assert data["deleted_count"] >= 1


@pytest.mark.asyncio
async def test_get_order_messages(client: AsyncClient, auth_headers, admin_headers, test_item):
    """Test getting order messages."""
    # Add to cart and create order
    await client.post(
        "/api/v1/cart/items",
        headers=auth_headers,
        json={"item_id": test_item.id, "quantity": 1}
    )
    
    order_response = await client.post(
        "/api/v1/orders",
        headers=auth_headers,
        json={"shipping_address": "Test Address"}
    )
    order_id = order_response.json()["id"]
    
    # Get admin ID
    admin_me = await client.get("/api/v1/auth/me", headers=admin_headers)
    admin_id = admin_me.json()["id"]
    
    # Send message about order
    await client.post(
        "/api/v1/chat/messages",
        headers=auth_headers,
        json={
            "receiver_id": admin_id,
            "text": "Order question",
            "order_id": order_id
        }
    )
    
    # Get order messages
    response = await client.get(
        f"/api/v1/chat/orders/{order_id}/messages",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "messages" in data
    assert len(data["messages"]) >= 1

