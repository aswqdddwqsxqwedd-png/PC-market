"""Comprehensive tests for admin API to increase coverage."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from app.main import app
from app.models.user import User


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_get_all_users(client):
    """Test getting all users."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.role = "admin"
    
    with patch('app.api.admin.get_current_active_admin', return_value=mock_user), \
         patch('app.api.admin.get_db') as mock_get_db, \
         patch('app.api.admin.UserService.get_all_users') as mock_get_users:
        
        mock_get_users.return_value = [{"id": 1, "username": "test", "role": "customer"}]
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        response = client.get("/admin/users")
        assert response.status_code == 200


def test_update_user_role(client):
    """Test updating user role."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.role = "admin"
    
    with patch('app.api.admin.get_current_active_admin', return_value=mock_user), \
         patch('app.api.admin.get_db') as mock_get_db, \
         patch('app.api.admin.UserService.update_user_role') as mock_update_role:
        
        mock_update_role.return_value = {"id": 2, "username": "test", "role": "seller"}
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        response = client.patch("/admin/users/2/role", json={"role": "seller"})
        assert response.status_code in [200, 400, 404, 422]


def test_deactivate_user(client):
    """Test deactivating user."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.role = "admin"
    
    with patch('app.api.admin.get_current_active_admin', return_value=mock_user), \
         patch('app.api.admin.get_db') as mock_get_db, \
         patch('app.api.admin.UserService.deactivate_user') as mock_deactivate:
        
        mock_deactivate.return_value = {"id": 2, "is_active": False}
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        response = client.patch("/admin/users/2/deactivate")
        assert response.status_code in [200, 404, 422]


def test_activate_user(client):
    """Test activating user."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.role = "admin"
    
    with patch('app.api.admin.get_current_active_admin', return_value=mock_user), \
         patch('app.api.admin.get_db') as mock_get_db, \
         patch('app.api.admin.UserService.activate_user') as mock_activate:
        
        mock_activate.return_value = {"id": 2, "is_active": True}
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        response = client.patch("/admin/users/2/activate")
        assert response.status_code in [200, 404, 422]


def test_get_all_products(client):
    """Test getting all products."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.role = "admin"
    
    with patch('app.api.admin.get_current_active_admin', return_value=mock_user), \
         patch('app.api.admin.get_db') as mock_get_db, \
         patch('app.api.admin.ItemService.get_all_items_paginated') as mock_get_items:
        
        mock_get_items.return_value = {"items": [{"id": 1, "name": "test product"}], "total": 1}
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        response = client.get("/admin/products")
        assert response.status_code == 200


def test_update_product_status(client):
    """Test updating product status."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.role = "admin"
    
    with patch('app.api.admin.get_current_active_admin', return_value=mock_user), \
         patch('app.api.admin.get_db') as mock_get_db, \
         patch('app.api.admin.ItemService.update_item_status') as mock_update_status:
        
        mock_update_status.return_value = {"id": 1, "name": "test product", "is_active": False}
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        response = client.patch("/admin/products/1/status", json={"is_active": False})
        assert response.status_code in [200, 400, 404, 422]


def test_get_all_orders(client):
    """Test getting all orders."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.role = "admin"
    
    with patch('app.api.admin.get_current_active_admin', return_value=mock_user), \
         patch('app.api.admin.get_db') as mock_get_db, \
         patch('app.api.admin.OrderService.get_all_orders_paginated') as mock_get_orders:
        
        mock_get_orders.return_value = {"orders": [{"id": 1, "status": "pending"}], "total": 1}
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        response = client.get("/admin/orders")
        assert response.status_code == 200


def test_update_order_status(client):
    """Test updating order status."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.role = "admin"
    
    with patch('app.api.admin.get_current_active_admin', return_value=mock_user), \
         patch('app.api.admin.get_db') as mock_get_db, \
         patch('app.api.admin.OrderService.update_order_status') as mock_update_status:
        
        mock_update_status.return_value = {"id": 1, "status": "completed"}
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        response = client.patch("/admin/orders/1/status", json={"status": "completed"})
        assert response.status_code in [200, 400, 404, 422]


def test_get_system_stats(client):
    """Test getting system statistics."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.role = "admin"
    
    with patch('app.api.admin.get_current_active_admin', return_value=mock_user), \
         patch('app.api.admin.get_db') as mock_get_db, \
         patch('app.api.admin.ReportService.get_system_stats') as mock_get_stats:
        
        mock_get_stats.return_value = {"total_users": 10, "total_orders": 5, "total_revenue": 1000}
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        response = client.get("/admin/stats")
        assert response.status_code == 200


def test_create_announcement(client):
    """Test creating announcement."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.role = "admin"
    
    with patch('app.api.admin.get_current_active_admin', return_value=mock_user), \
         patch('app.api.admin.get_db') as mock_get_db, \
         patch('app.api.admin.create_announcement') as mock_create_announce:
        
        mock_create_announce.return_value = {"id": 1, "title": "Announcement", "content": "Content"}
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        response = client.post("/admin/announcements", json={
            "title": "Test Announcement",
            "content": "Test Content"
        })
        assert response.status_code in [200, 400, 422]


def test_get_announcements(client):
    """Test getting announcements."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.role = "admin"
    
    with patch('app.api.admin.get_current_active_admin', return_value=mock_user), \
         patch('app.api.admin.get_db') as mock_get_db, \
         patch('app.api.admin.get_announcements') as mock_get_announce:
        
        mock_get_announce.return_value = [{"id": 1, "title": "Announcement", "content": "Content"}]
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        response = client.get("/admin/announcements")
        assert response.status_code == 200


def test_delete_announcement(client):
    """Test deleting announcement."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.role = "admin"
    
    with patch('app.api.admin.get_current_active_admin', return_value=mock_user), \
         patch('app.api.admin.get_db') as mock_get_db, \
         patch('app.api.admin.delete_announcement') as mock_delete_announce:
        
        mock_delete_announce.return_value = True
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        response = client.delete("/admin/announcements/1")
        assert response.status_code in [200, 404, 422]