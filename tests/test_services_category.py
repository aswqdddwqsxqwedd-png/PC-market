"""Tests for CategoryService."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.category_service import CategoryService, slugify
from app.models import Category, Item
from app.schemas import CategoryCreate, CategoryUpdate
from app.core.exceptions import NotFoundError, ConflictError


@pytest.mark.asyncio
async def test_slugify():
    """Test slugify function."""
    assert slugify("Test Category") == "test-category"
    assert slugify("Test  Category") == "test-category"
    assert slugify("Test-Category") == "test-category"
    assert slugify("Test@Category#123") == "testcategory123"


@pytest.mark.asyncio
async def test_get_by_id_not_found(db_session: AsyncSession):
    """Test getting non-existent category."""
    service = CategoryService(db_session)
    category = await service.get_by_id(999)
    assert category is None


@pytest.mark.asyncio
async def test_get_by_slug_not_found(db_session: AsyncSession):
    """Test getting category by non-existent slug."""
    service = CategoryService(db_session)
    category = await service.get_by_slug("non-existent")
    assert category is None


@pytest.mark.asyncio
async def test_get_by_slug(db_session: AsyncSession):
    """Test getting category by slug."""
    category = Category(
        name="Test Category",
        slug="test-category",
        description="Test"
    )
    db_session.add(category)
    await db_session.flush()
    
    service = CategoryService(db_session)
    found = await service.get_by_slug("test-category")
    assert found is not None
    assert found.id == category.id


@pytest.mark.asyncio
async def test_get_all_empty(db_session: AsyncSession):
    """Test getting all categories when empty."""
    service = CategoryService(db_session)
    categories = await service.get_all()
    assert categories == []


@pytest.mark.asyncio
async def test_get_with_counts(db_session: AsyncSession, test_category):
    """Test getting categories with item counts."""
    item = Item(
        name="Test Item",
        description="Test",
        price=1000.0,
        quantity=10,
        category_id=test_category.id,
        owner_id=1
    )
    db_session.add(item)
    await db_session.flush()
    
    service = CategoryService(db_session)
    categories = await service.get_with_counts()
    assert len(categories) > 0
    test_cat = next((c for c in categories if c["id"] == test_category.id), None)
    assert test_cat is not None
    assert test_cat["items_count"] == 1


@pytest.mark.asyncio
async def test_count(db_session: AsyncSession):
    """Test counting categories."""
    service = CategoryService(db_session)
    count = await service.count()
    assert count >= 0


@pytest.mark.asyncio
async def test_create_with_slug(db_session: AsyncSession):
    """Test creating category with provided slug."""
    service = CategoryService(db_session)
    category_data = CategoryCreate(
        name="Test Category",
        slug="custom-slug",
        description="Test"
    )
    category = await service.create(category_data)
    assert category.slug == "custom-slug"


@pytest.mark.asyncio
async def test_create_without_slug(db_session: AsyncSession):
    """Test creating category without slug (auto-generate)."""
    service = CategoryService(db_session)
    category_data = CategoryCreate(
        name="Test Category",
        description="Test"
    )
    category = await service.create(category_data)
    assert category.slug == "test-category"


@pytest.mark.asyncio
async def test_create_duplicate_slug(db_session: AsyncSession):
    """Test creating category with duplicate slug."""
    category = Category(
        name="Existing",
        slug="test-slug",
        description="Test"
    )
    db_session.add(category)
    await db_session.flush()
    
    service = CategoryService(db_session)
    category_data = CategoryCreate(
        name="New Category",
        slug="test-slug",
        description="Test"
    )
    with pytest.raises(ConflictError):
        await service.create(category_data)


@pytest.mark.asyncio
async def test_update_not_found(db_session: AsyncSession):
    """Test updating non-existent category."""
    service = CategoryService(db_session)
    with pytest.raises(NotFoundError):
        await service.update(999, CategoryUpdate(name="New Name"))


@pytest.mark.asyncio
async def test_update_name_auto_slug(db_session: AsyncSession, test_category):
    """Test updating category name auto-generates slug."""
    service = CategoryService(db_session)
    updated = await service.update(test_category.id, CategoryUpdate(name="New Name"))
    assert updated.name == "New Name"
    assert updated.slug == "new-name"


@pytest.mark.asyncio
async def test_update_with_slug(db_session: AsyncSession, test_category):
    """Test updating category with provided slug."""
    service = CategoryService(db_session)
    updated = await service.update(test_category.id, CategoryUpdate(name="New Name", slug="custom-slug"))
    assert updated.name == "New Name"
    assert updated.slug == "custom-slug"


@pytest.mark.asyncio
async def test_delete_not_found(db_session: AsyncSession):
    """Test deleting non-existent category."""
    service = CategoryService(db_session)
    with pytest.raises(NotFoundError):
        await service.delete(999)


@pytest.mark.asyncio
async def test_delete(db_session: AsyncSession, test_category):
    """Test deleting category."""
    service = CategoryService(db_session)
    result = await service.delete(test_category.id)
    assert result is True
    
    found = await service.get_by_id(test_category.id)
    assert found is None

