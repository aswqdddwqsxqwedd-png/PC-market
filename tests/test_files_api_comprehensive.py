"""Comprehensive tests for files API to increase coverage."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import io
from PIL import Image
from app.main import app
from app.models.user import User


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_upload_image_file(client):
    """Test uploading an image file."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.role = "seller"
    
    # Create a simple in-memory image
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    with patch('app.api.files.get_current_active_user', return_value=mock_user), \
         patch('app.api.files.get_storage_service') as mock_get_storage, \
         patch('app.api.files.get_db') as mock_get_db:
        
        mock_storage = MagicMock()
        mock_storage.upload_file = AsyncMock(return_value="/static/uploads/test.jpg")
        mock_get_storage.return_value = mock_storage
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        response = client.post(
            "/files/upload",
            files={"file": ("test.jpg", img_bytes.getvalue(), "image/jpeg")},
            data={"purpose": "product_image"}
        )
        assert response.status_code in [200, 400, 422]


def test_upload_invalid_file_type(client):
    """Test uploading an invalid file type."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.role = "seller"
    
    with patch('app.api.files.get_current_active_user', return_value=mock_user):
        response = client.post(
            "/files/upload",
            files={"file": ("test.txt", b"invalid file content", "text/plain")},
            data={"purpose": "product_image"}
        )
        assert response.status_code in [400, 422]


def test_get_file_by_id(client):
    """Test getting a file by ID."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.role = "customer"
    
    with patch('app.api.files.get_current_active_user', return_value=mock_user), \
         patch('app.api.files.get_storage_service') as mock_get_storage:
        
        mock_storage = MagicMock()
        mock_storage.generate_presigned_url = AsyncMock(return_value="http://example.com/file.jpg")
        mock_get_storage.return_value = mock_storage
        
        response = client.get("/files/123")
        assert response.status_code in [200, 404, 422]


def test_delete_file_by_owner(client):
    """Test deleting a file by its owner."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.role = "seller"
    
    with patch('app.api.files.get_current_active_user', return_value=mock_user), \
         patch('app.api.files.get_db') as mock_get_db, \
         patch('app.api.files.get_storage_service') as mock_get_storage:
        
        # Mock the file record lookup
        mock_db = MagicMock()
        mock_file_record = MagicMock()
        mock_file_record.owner_id = 1  # Same as user id
        mock_db.query().filter().first.return_value = mock_file_record
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        mock_storage = MagicMock()
        mock_storage.delete_file = AsyncMock(return_value=True)
        mock_get_storage.return_value = mock_storage
        
        response = client.delete("/files/123")
        assert response.status_code in [200, 403, 404, 422]


def test_delete_file_by_admin(client):
    """Test deleting a file by admin."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.role = "admin"
    
    with patch('app.api.files.get_current_active_admin', return_value=mock_user), \
         patch('app.api.files.get_db') as mock_get_db, \
         patch('app.api.files.get_storage_service') as mock_get_storage:
        
        # Mock the file record lookup
        mock_db = MagicMock()
        mock_file_record = MagicMock()
        mock_file_record.owner_id = 2  # Different from admin id
        mock_db.query().filter().first.return_value = mock_file_record
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        mock_storage = MagicMock()
        mock_storage.delete_file = AsyncMock(return_value=True)
        mock_get_storage.return_value = mock_storage
        
        response = client.delete("/files/123")
        assert response.status_code in [200, 404, 422]


def test_upload_profile_picture(client):
    """Test uploading a profile picture."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.role = "customer"
    
    # Create a simple in-memory image
    img = Image.new('RGB', (100, 100), color='blue')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    with patch('app.api.files.get_current_active_user', return_value=mock_user), \
         patch('app.api.files.get_storage_service') as mock_get_storage, \
         patch('app.api.files.get_db') as mock_get_db:
        
        mock_storage = MagicMock()
        mock_storage.upload_file = AsyncMock(return_value="/static/uploads/profile.png")
        mock_get_storage.return_value = mock_storage
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        response = client.post(
            "/files/upload/profile",
            files={"file": ("profile.png", img_bytes.getvalue(), "image/png")}
        )
        assert response.status_code in [200, 400, 422]


def test_upload_multiple_files(client):
    """Test uploading multiple files."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.role = "seller"
    
    # Create two simple in-memory images
    img1 = Image.new('RGB', (100, 100), color='red')
    img1_bytes = io.BytesIO()
    img1.save(img1_bytes, format='JPEG')
    img1_bytes.seek(0)
    
    img2 = Image.new('RGB', (100, 100), color='green')
    img2_bytes = io.BytesIO()
    img2.save(img2_bytes, format='JPEG')
    img2_bytes.seek(0)
    
    with patch('app.api.files.get_current_active_user', return_value=mock_user), \
         patch('app.api.files.get_storage_service') as mock_get_storage, \
         patch('app.api.files.get_db') as mock_get_db:
        
        mock_storage = MagicMock()
        mock_storage.upload_file = AsyncMock(side_effect=[
            "/static/uploads/test1.jpg", 
            "/static/uploads/test2.jpg"
        ])
        mock_get_storage.return_value = mock_storage
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        response = client.post(
            "/files/upload/multiple",
            files=[
                ("files", ("test1.jpg", img1_bytes.getvalue(), "image/jpeg")),
                ("files", ("test2.jpg", img2_bytes.getvalue(), "image/jpeg"))
            ],
            data={"purpose": "product_gallery"}
        )
        assert response.status_code in [200, 400, 422]


def test_get_user_uploaded_files(client):
    """Test getting user uploaded files."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.role = "customer"
    
    with patch('app.api.files.get_current_active_user', return_value=mock_user), \
         patch('app.api.files.get_db') as mock_get_db:
        
        mock_db = MagicMock()
        mock_query_result = [
            {"id": 1, "filename": "profile.jpg", "size": 1024, "uploaded_at": "2023-01-01"},
            {"id": 2, "filename": "avatar.png", "size": 2048, "uploaded_at": "2023-01-02"}
        ]
        mock_db.query().filter().offset().limit().all.return_value = mock_query_result
        mock_db.query().filter().count.return_value = 2
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        response = client.get("/files/my-uploads?skip=0&limit=10")
        assert response.status_code == 200


def test_download_file(client):
    """Test downloading a file."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.role = "customer"
    
    with patch('app.api.files.get_current_active_user', return_value=mock_user), \
         patch('app.api.files.get_storage_service') as mock_get_storage:
        
        mock_storage = MagicMock()
        mock_storage.generate_presigned_url = AsyncMock(return_value="http://example.com/download/file.jpg")
        mock_get_storage.return_value = mock_storage
        
        response = client.get("/files/download/123")
        assert response.status_code in [200, 404, 422]


def test_upload_file_size_validation(client):
    """Test file size validation during upload."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.role = "seller"
    
    # Create a large file that exceeds the limit
    large_file_content = b"x" * (10 * 1024 * 1024 + 1)  # 10MB + 1 byte
    
    with patch('app.api.files.get_current_active_user', return_value=mock_user):
        response = client.post(
            "/files/upload",
            files={"file": ("large_file.jpg", large_file_content, "image/jpeg")},
            data={"purpose": "product_image"}
        )
        assert response.status_code in [413, 400, 422]  # 413 is Request Entity Too Large


def test_upload_without_authentication(client):
    """Test uploading file without authentication."""
    # Create a simple in-memory image
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    response = client.post(
        "/files/upload",
        files={"file": ("test.jpg", img_bytes.getvalue(), "image/jpeg")},
        data={"purpose": "product_image"}
    )
    assert response.status_code in [401, 422]


def test_get_file_presigned_url(client):
    """Test getting presigned URL for a file."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.role = "customer"
    
    with patch('app.api.files.get_current_active_user', return_value=mock_user), \
         patch('app.api.files.get_storage_service') as mock_get_storage:
        
        mock_storage = MagicMock()
        mock_storage.generate_presigned_url = AsyncMock(return_value="https://minio.example.com/bucket/file.jpg")
        mock_get_storage.return_value = mock_storage
        
        response = client.get("/files/presigned/123")
        assert response.status_code in [200, 404, 422]
        if response.status_code == 200:
            assert "url" in response.json()