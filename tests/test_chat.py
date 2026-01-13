"""Tests for chat endpoints."""
import pytest
from httpx import AsyncClient
from app.models import UserRole


@pytest.mark.asyncio
async def test_send_message(client: AsyncClient, auth_headers, admin_headers):
    """Test sending a message."""
    # Get current user
    me_response = await client.get("/api/v1/auth/me", headers=auth_headers)
    sender_id = me_response.json()["id"]
    
    # Get admin user
    admin_response = await client.get("/api/v1/auth/me", headers=admin_headers)
    receiver_id = admin_response.json()["id"]
    
    # Send message
    response = await client.post(
        "/api/v1/chat/messages",
        headers=auth_headers,
        json={
            "receiver_id": receiver_id,
            "text": "Test message"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["text"] == "Test message"
    assert data["sender_id"] == sender_id
    assert data["receiver_id"] == receiver_id


@pytest.mark.asyncio
async def test_get_conversations(client: AsyncClient, auth_headers, admin_headers):
    """Test getting user conversations."""
    # Send a message first
    admin_response = await client.get("/api/v1/auth/me", headers=admin_headers)
    admin_id = admin_response.json()["id"]
    
    await client.post(
        "/api/v1/chat/messages",
        headers=auth_headers,
        json={
            "receiver_id": admin_id,
            "text": "Test message"
        }
    )
    
    # Get conversations
    response = await client.get("/api/v1/chat/conversations", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "conversations" in data
    assert isinstance(data["conversations"], list)


@pytest.mark.asyncio
async def test_get_conversation_messages(client: AsyncClient, auth_headers, admin_headers):
    """Test getting messages from a conversation."""
    # Get users
    me_response = await client.get("/api/v1/auth/me", headers=auth_headers)
    sender_id = me_response.json()["id"]
    
    admin_response = await client.get("/api/v1/auth/me", headers=admin_headers)
    receiver_id = admin_response.json()["id"]
    
    # Send message
    await client.post(
        "/api/v1/chat/messages",
        headers=auth_headers,
        json={
            "receiver_id": receiver_id,
            "text": "Test message"
        }
    )
    
    # Get conversation messages
    response = await client.get(
        f"/api/v1/chat/conversations/{receiver_id}/messages",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "messages" in data
    assert len(data["messages"]) > 0


@pytest.mark.asyncio
async def test_connect_to_support(client: AsyncClient, auth_headers, test_support):
    """Test connecting to support."""
    # test_support fixture ensures support user exists
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
async def test_get_support_conversations(client: AsyncClient, support_headers):
    """Test getting support conversations (for support/admin users)."""
    response = await client.get(
        "/api/v1/chat/support/conversations",
        headers=support_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "conversations" in data
    assert isinstance(data["conversations"], list)


@pytest.mark.asyncio
async def test_mark_messages_as_read(client: AsyncClient, auth_headers, admin_headers):
    """Test marking messages as read."""
    # Get users
    me_response = await client.get("/api/v1/auth/me", headers=auth_headers)
    sender_id = me_response.json()["id"]
    
    admin_response = await client.get("/api/v1/auth/me", headers=admin_headers)
    receiver_id = admin_response.json()["id"]
    
    # Send message
    msg_response = await client.post(
        "/api/v1/chat/messages",
        headers=auth_headers,
        json={
            "receiver_id": receiver_id,
            "text": "Test message"
        }
    )
    message_id = msg_response.json()["id"]
    
    # Mark as read
    response = await client.post(
        f"/api/v1/chat/messages/{message_id}/read",
        headers=admin_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert data["count"] > 0


@pytest.mark.asyncio
async def test_get_support_status(client: AsyncClient, support_headers):
    """Test getting support online status."""
    response = await client.get("/api/v1/chat/support/status", headers=support_headers)
    assert response.status_code == 200
    data = response.json()
    assert "is_online" in data


@pytest.mark.asyncio
async def test_get_support_conversation_messages(client: AsyncClient, auth_headers, support_headers):        
    """Test getting support conversation messages."""
    # Send message to support
    support_response = await client.get("/api/v1/auth/me", headers=support_headers)
    support_id = support_response.json()["id"]
    
    me_response = await client.get("/api/v1/auth/me", headers=auth_headers)
    user_id = me_response.json()["id"]
    
    await client.post(
        "/api/v1/chat/messages",
        headers=auth_headers,
        json={
            "receiver_id": support_id,
            "text": "Support message"
        }
    )
    
    # Get conversation messages using the regular endpoint
    response = await client.get(
        f"/api/v1/chat/conversations/{user_id}/messages",
        headers=support_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "messages" in data

