"""Tests for WebSocket connection manager."""
import pytest
from fastapi import WebSocket
from app.websocket.connection_manager import ConnectionManager
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def manager():
    """Create ConnectionManager instance."""
    return ConnectionManager()


@pytest.fixture
def mock_websocket():
    """Create mock WebSocket."""
    ws = AsyncMock(spec=WebSocket)
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    ws.send_json = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.mark.asyncio
async def test_connect(manager, mock_websocket):
    """Test connecting a user."""
    user_id = 1
    await manager.connect(mock_websocket, user_id)
    
    assert manager.is_connected(user_id)
    mock_websocket.accept.assert_called_once()


@pytest.mark.asyncio
async def test_disconnect(manager, mock_websocket):
    """Test disconnecting a user."""
    user_id = 1
    await manager.connect(mock_websocket, user_id)
    manager.disconnect(mock_websocket)
    
    assert not manager.is_connected(user_id)


@pytest.mark.asyncio
async def test_is_connected(manager, mock_websocket):
    """Test checking if user is connected."""
    user_id = 1
    assert not manager.is_connected(user_id)
    
    await manager.connect(mock_websocket, user_id)
    assert manager.is_connected(user_id)
    
    manager.disconnect(mock_websocket)
    assert not manager.is_connected(user_id)


@pytest.mark.asyncio
async def test_send_personal_message(manager, mock_websocket):
    """Test sending personal message."""
    user_id = 1
    await manager.connect(mock_websocket, user_id)
    
    message = {"type": "test", "data": "test"}
    await manager.send_personal_message(message, user_id)
    
    mock_websocket.send_json.assert_called_once_with(message)


@pytest.mark.asyncio
async def test_send_personal_message_not_connected(manager):
    """Test sending message to non-connected user."""
    user_id = 999
    message = {"type": "test", "data": "test"}
    
    # Should not raise error
    await manager.send_personal_message(message, user_id)


@pytest.mark.asyncio
async def test_broadcast_to_order_participants(manager, mock_websocket):
    """Test broadcasting message to order participants."""
    user_id = 1
    await manager.connect(mock_websocket, user_id)
    
    message = {"type": "order_message", "data": "test"}
    await manager.broadcast_to_order_participants(message, order_id=1, sender_id=2, participant_ids=[1, 2])
    
    mock_websocket.send_json.assert_called_once_with(message)


@pytest.mark.asyncio
async def test_get_connected_users(manager, mock_websocket):
    """Test getting list of connected users."""
    user_id = 1
    assert len(manager.get_connected_users()) == 0
    
    await manager.connect(mock_websocket, user_id)
    connected = manager.get_connected_users()
    assert user_id in connected
    assert len(connected) == 1

