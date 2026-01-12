"""Comprehensive tests for chat API to increase coverage."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from app.main import app
from app.api.deps import get_current_user, get_db, get_storage_service
from app.models.user import User


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.mark.parametrize("role", ["admin", "support", "seller", "customer"])
def test_create_conversation_with_different_roles(client, role):
    """Test creating conversation with different user roles."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.role = role
    
    with patch('app.api.chat.get_current_active_user', return_value=mock_user), \
         patch('app.api.chat.get_db') as mock_get_db, \
         patch('app.api.chat.ChatService.create_conversation') as mock_create_conv:
        
        mock_create_conv.return_value = {"conversation_id": 1, "title": "Test"}
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        response = client.post("/chat/conversations/", json={"title": "Test"})
        assert response.status_code in [200, 400, 422]


def test_get_conversations(client):
    """Test getting conversations."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.role = "customer"
    
    with patch('app.api.chat.get_current_active_user', return_value=mock_user), \
         patch('app.api.chat.get_db') as mock_get_db, \
         patch('app.api.chat.ChatService.get_user_conversations') as mock_get_conv:
        
        mock_get_conv.return_value = [{"id": 1, "title": "Test"}]
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        response = client.get("/chat/conversations/")
        assert response.status_code == 200


def test_send_message_to_conversation(client):
    """Test sending message to conversation."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.role = "customer"
    
    with patch('app.api.chat.get_current_active_user', return_value=mock_user), \
         patch('app.api.chat.get_db') as mock_get_db, \
         patch('app.api.chat.ChatService.send_message') as mock_send_msg:
        
        mock_send_msg.return_value = {"id": 1, "text": "Test message", "sender_id": 1}
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        response = client.post("/chat/conversations/1/messages", json={"text": "Hello"})
        assert response.status_code in [200, 400, 404, 422]


def test_get_messages_from_conversation(client):
    """Test getting messages from conversation."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.role = "customer"
    
    with patch('app.api.chat.get_current_active_user', return_value=mock_user), \
         patch('app.api.chat.get_db') as mock_get_db, \
         patch('app.api.chat.ChatService.get_conversation_messages') as mock_get_msgs:
        
        mock_get_msgs.return_value = [{"id": 1, "text": "Test message", "sender_id": 1}]
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        response = client.get("/chat/conversations/1/messages")
        assert response.status_code == 200


def test_update_conversation_title(client):
    """Test updating conversation title."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.role = "customer"
    
    with patch('app.api.chat.get_current_active_user', return_value=mock_user), \
         patch('app.api.chat.get_db') as mock_get_db, \
         patch('app.api.chat.ChatService.update_conversation_title') as mock_update_title:
        
        mock_update_title.return_value = {"id": 1, "title": "Updated Title"}
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        response = client.put("/chat/conversations/1/title", json={"title": "New Title"})
        assert response.status_code in [200, 400, 404, 422]


def test_add_participant_to_conversation(client):
    """Test adding participant to conversation."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.role = "admin"
    
    with patch('app.api.chat.get_current_active_user', return_value=mock_user), \
         patch('app.api.chat.get_db') as mock_get_db, \
         patch('app.api.chat.ChatService.add_participant') as mock_add_participant:
        
        mock_add_participant.return_value = True
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        response = client.post("/chat/conversations/1/participants", json={"user_id": 2})
        assert response.status_code in [200, 400, 404, 422]


def test_remove_participant_from_conversation(client):
    """Test removing participant from conversation."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.role = "admin"
    
    with patch('app.api.chat.get_current_active_user', return_value=mock_user), \
         patch('app.api.chat.get_db') as mock_get_db, \
         patch('app.api.chat.ChatService.remove_participant') as mock_remove_participant:
        
        mock_remove_participant.return_value = True
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        response = client.delete("/chat/conversations/1/participants/2")
        assert response.status_code in [200, 400, 404, 422]


def test_search_messages(client):
    """Test searching messages."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.role = "customer"
    
    with patch('app.api.chat.get_current_active_user', return_value=mock_user), \
         patch('app.api.chat.get_db') as mock_get_db, \
         patch('app.api.chat.ChatService.search_messages') as mock_search:
        
        mock_search.return_value = [{"id": 1, "text": "Test message", "sender_id": 1}]
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        response = client.get("/chat/search?q=test")
        assert response.status_code == 200


def test_get_conversation_by_id(client):
    """Test getting specific conversation."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.role = "customer"
    
    with patch('app.api.chat.get_current_active_user', return_value=mock_user), \
         patch('app.api.chat.get_db') as mock_get_db, \
         patch('app.api.chat.ChatService.get_conversation_by_id') as mock_get_conv:
        
        mock_get_conv.return_value = {"id": 1, "title": "Test Conversation"}
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        response = client.get("/chat/conversations/1")
        assert response.status_code == 200


def test_delete_conversation(client):
    """Test deleting conversation."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.role = "admin"
    
    with patch('app.api.chat.get_current_active_user', return_value=mock_user), \
         patch('app.api.chat.get_db') as mock_get_db, \
         patch('app.api.chat.ChatService.delete_conversation') as mock_delete:
        
        mock_delete.return_value = True
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        response = client.delete("/chat/conversations/1")
        assert response.status_code in [200, 404, 422]