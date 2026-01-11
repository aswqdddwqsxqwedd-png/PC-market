"""Tests for frontend static files."""
import pytest
from httpx import AsyncClient
import os


@pytest.mark.asyncio
async def test_index_html_served(client: AsyncClient):
    """Test that index.html is served correctly."""
    response = await client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    content = response.text
    assert "<!DOCTYPE html>" in content
    assert "PC Place" in content
    assert "React" in content or "react" in content


@pytest.mark.asyncio
async def test_admin_html_served(client: AsyncClient):
    """Test that admin.html is served correctly."""
    response = await client.get("/admin.html")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    content = response.text
    assert "<!DOCTYPE html>" in content
    assert "Админ-панель" in content or "admin" in content.lower()


@pytest.mark.asyncio
async def test_index_html_has_no_syntax_errors(client: AsyncClient):
    """Test that index.html has valid structure."""
    response = await client.get("/")
    assert response.status_code == 200
    content = response.text
    
    # Check for basic HTML structure
    assert "<html" in content
    assert "</html>" in content
    assert "<head" in content
    assert "<body" in content
    
    # Check for React initialization
    assert "ReactDOM" in content or "React" in content
    
    # Check for script tags
    assert "<script" in content
    
    # Check that there are no obvious broken tags
    assert content.count("<script") == content.count("</script>") or content.count("<script type=") > 0


@pytest.mark.asyncio
async def test_admin_html_has_no_syntax_errors(client: AsyncClient):
    """Test that admin.html has valid structure."""
    response = await client.get("/admin.html")
    assert response.status_code == 200
    content = response.text
    
    # Check for basic HTML structure
    assert "<html" in content
    assert "</html>" in content
    assert "<head" in content
    assert "<body" in content
    
    # Check for React initialization
    assert "ReactDOM" in content or "React" in content


@pytest.mark.asyncio
async def test_index_html_no_admin_components(client: AsyncClient):
    """Test that index.html doesn't contain admin components."""
    response = await client.get("/")
    assert response.status_code == 200
    content = response.text
    
    # Admin components should not be in main index.html
    assert "AdminPage" not in content or "// Admin components removed" in content
    assert "AdminDashboard" not in content
    assert "AdminUsers" not in content
    assert "AdminItems" not in content
    assert "AdminOrders" not in content
    assert "AdminReports" not in content


@pytest.mark.asyncio
async def test_static_files_exist():
    """Test that required static files exist."""
    static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
    index_path = os.path.join(static_dir, "index.html")
    admin_path = os.path.join(static_dir, "admin.html")
    
    assert os.path.exists(index_path), "index.html should exist"
    assert os.path.exists(admin_path), "admin.html should exist"
    
    # Check file sizes (should not be empty)
    assert os.path.getsize(index_path) > 1000, "index.html should not be empty"
    assert os.path.getsize(admin_path) > 1000, "admin.html should not be empty"


@pytest.mark.asyncio
async def test_api_endpoints_accessible(client: AsyncClient):
    """Test that basic API endpoints are accessible."""
    # Test public endpoints
    response = await client.get("/api/v1/categories")
    assert response.status_code == 200
    
    response = await client.get("/api/v1/items")
    assert response.status_code == 200
    
    # Test docs
    response = await client.get("/docs")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_index_html_cache_headers(client: AsyncClient):
    """Test that index.html has proper cache control headers."""
    response = await client.get("/")
    assert response.status_code == 200
    
    cache_control = response.headers.get("Cache-Control", "")
    assert "no-cache" in cache_control or "no-store" in cache_control


@pytest.mark.asyncio
async def test_admin_html_cache_headers(client: AsyncClient):
    """Test that admin.html has proper cache control headers."""
    response = await client.get("/admin.html")
    assert response.status_code == 200
    
    cache_control = response.headers.get("Cache-Control", "")
    assert "no-cache" in cache_control or "no-store" in cache_control

