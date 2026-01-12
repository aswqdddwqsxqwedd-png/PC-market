"""Comprehensive tests for storage_service.py to increase coverage."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import io
from PIL import Image
from app.services.storage_service import (
    StorageService,
    get_storage_service,
    generate_filename,
    validate_file_type,
    resize_image,
    save_file_locally
)


@pytest.fixture
def mock_minio_client():
    """Mock MinIO client for testing."""
    mock_client = MagicMock()
    mock_client.bucket_exists = MagicMock(return_value=True)
    mock_client.make_bucket = MagicMock()
    mock_client.fput_object = MagicMock()
    mock_client.presigned_get_object = MagicMock(return_value="http://presigned-url.com/file")
    mock_client.presigned_put_object = MagicMock(return_value="http://presigned-upload-url.com/file")
    mock_client.remove_object = MagicMock()
    return mock_client


@pytest.mark.asyncio
async def test_storage_service_initialization(mock_minio_client):
    """Test StorageService initialization."""
    service = StorageService(minio_client=mock_minio_client)
    assert service.minio_client == mock_minio_client


@pytest.mark.asyncio
async def test_upload_file_minio_success(mock_minio_client):
    """Test successful file upload to MinIO."""
    service = StorageService(minio_client=mock_minio_client)
    
    # Create a mock file-like object
    mock_file = AsyncMock()
    mock_file.filename = "test.jpg"
    mock_file.read = AsyncMock(return_value=b"fake image data")
    
    with patch('app.services.storage_service.validate_file_type', return_value=True), \
         patch('app.services.storage_service.resize_image') as mock_resize, \
         patch('app.services.storage_service.generate_filename', return_value="unique_test.jpg"), \
         patch('tempfile.NamedTemporaryFile') as mock_tempfile:
        
        mock_tempfile.return_value.__enter__.return_value.name = "/tmp/test.jpg"
        
        result = await service.upload_file(mock_file)
        assert result is not None


@pytest.mark.asyncio
async def test_upload_file_local_success():
    """Test successful file upload to local storage."""
    service = StorageService(minio_client=None)  # Using local storage
    
    mock_file = AsyncMock()
    mock_file.filename = "test.jpg"
    mock_file.read = AsyncMock(return_value=b"fake image data")
    
    with patch('app.services.storage_service.validate_file_type', return_value=True), \
         patch('app.services.storage_service.resize_image'), \
         patch('app.services.storage_service.generate_filename', return_value="unique_test.jpg"), \
         patch('app.services.storage_service.save_file_locally', return_value="/static/uploads/unique_test.jpg"):
        
        result = await service.upload_file(mock_file)
        assert result is not None


@pytest.mark.asyncio
async def test_delete_file_minio_success(mock_minio_client):
    """Test successful file deletion from MinIO."""
    service = StorageService(minio_client=mock_minio_client)
    
    await service.delete_file("test.jpg")
    mock_minio_client.remove_object.assert_called_once()


@pytest.mark.asyncio
async def test_delete_file_local_success(tmp_path):
    """Test successful file deletion from local storage."""
    service = StorageService(minio_client=None)
    
    # Create a temporary file
    test_file = tmp_path / "test.jpg"
    test_file.write_text("test content")
    
    with patch('app.services.storage_service.UPLOAD_DIR', str(tmp_path)):
        result = await service.delete_file("test.jpg")
        assert result is True
        assert not test_file.exists()


@pytest.mark.asyncio
async def test_generate_presigned_url_minio_success(mock_minio_client):
    """Test generating presigned URL from MinIO."""
    service = StorageService(minio_client=mock_minio_client)
    
    result = await service.generate_presigned_url("test.jpg")
    assert result is not None


@pytest.mark.asyncio
async def test_generate_presigned_url_local_fallback():
    """Test presigned URL generation fallback for local storage."""
    service = StorageService(minio_client=None)
    
    result = await service.generate_presigned_url("test.jpg")
    assert result is not None


@pytest.mark.asyncio
async def test_generate_presigned_upload_url_minio_success(mock_minio_client):
    """Test generating presigned upload URL from MinIO."""
    service = StorageService(minio_client=mock_minio_client)
    
    result = await service.generate_presigned_upload_url("test.jpg")
    assert result is not None


def test_get_storage_service():
    """Test getting storage service instance."""
    service = get_storage_service()
    assert service is not None


def test_generate_filename():
    """Test filename generation."""
    filename = generate_filename("test.jpg")
    assert isinstance(filename, str)
    assert "test" in filename
    assert filename.endswith(".jpg")


def test_validate_file_type_valid():
    """Test valid file type validation."""
    assert validate_file_type("test.jpg") is True
    assert validate_file_type("test.png") is True
    assert validate_file_type("test.gif") is True
    assert validate_file_type("test.webp") is True


def test_validate_file_type_invalid():
    """Test invalid file type validation."""
    assert validate_file_type("test.txt") is False
    assert validate_file_type("test.pdf") is False
    assert validate_file_type("test.doc") is False


def test_resize_image():
    """Test image resizing functionality."""
    # Create a small test image
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    resized_img_bytes = resize_image(img_bytes.getvalue(), (50, 50))
    assert len(resized_img_bytes) > 0


def test_save_file_locally(tmp_path):
    """Test saving file locally."""
    test_data = b"test file content"
    file_path = tmp_path / "test.jpg"
    
    with patch('app.services.storage_service.UPLOAD_DIR', str(tmp_path)):
        result = save_file_locally(test_data, "test.jpg")
        assert result == f"/static/uploads/test.jpg"
        assert file_path.exists()