"""Quick tests for chat endpoints to boost coverage."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_conversations_pagination(client: AsyncClient, auth_headers, support_headers):
    """Test getting conversations with pagination."""
    # Send message first
    support_response = await client.get("/api/v1/auth/me", headers=support_headers)
    support_id = support_response.json()["id"]
    
    await client.post(
        "/api/v1/chat/messages",
        headers=auth_headers,
        json={"receiver_id": support_id, "text": "Test"}
    )
    
    # Test pagination
    response = await client.get(
        "/api/v1/chat/conversations?page=1&limit=10",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "conversations" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_get_conversation_messages_with_order(client: AsyncClient, auth_headers, admin_headers, test_item):
    """Test getting conversation messages with order_id."""
    # Create order
    await client.post(
        "/api/v1/cart/items",
        headers=auth_headers,
        json={"item_id": test_item.id, "quantity": 1}
    )
    order_response = await client.post(
        "/api/v1/orders",
        headers=auth_headers,
        json={"shipping_address": "Test"}
    )
    order_id = order_response.json()["id"]
    
    # Get admin ID
    admin_me = await client.get("/api/v1/auth/me", headers=admin_headers)
    admin_id = admin_me.json()["id"]
    
    # Send message with order_id
    await client.post(
        "/api/v1/chat/messages",
        headers=auth_headers,
        json={
            "receiver_id": admin_id,
            "text": "Order question",
            "order_id": order_id
        }
    )
    
    # Get messages with order_id
    response = await client.get(
        f"/api/v1/chat/conversations/{admin_id}/messages?order_id={order_id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "messages" in data


@pytest.mark.asyncio
async def test_connect_to_support_with_order(client: AsyncClient, auth_headers, test_item, test_support):
    """Test connecting to support with order_id."""
    # Create order
    await client.post(
        "/api/v1/cart/items",
        headers=auth_headers,
        json={"item_id": test_item.id, "quantity": 1}
    )
    order_response = await client.post(
        "/api/v1/orders",
        headers=auth_headers,
        json={"shipping_address": "Test"}
    )
    order_id = order_response.json()["id"]
    
    # Connect to support with order
    response = await client.post(
        f"/api/v1/chat/support/connect?order_id={order_id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "support_user_id" in data
    assert data["support_user_id"] == test_support.id
    assert data["order_id"] == order_id

