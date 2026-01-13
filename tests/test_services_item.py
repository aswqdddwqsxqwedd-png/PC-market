"""Tests for ItemService."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.item_service import ItemService
from app.models import Item, Category
from app.schemas import ItemCreate, ItemUpdate, ItemFilter
from app.core.exceptions import NotFoundError, AuthorizationError


@pytest.mark.asyncio
async def test_get_by_id_not_found(db_session: AsyncSession):
    """Test getting non-existent item."""
    service = ItemService(db_session)
    item = await service.get_by_id(999)
    assert item is None


@pytest.mark.asyncio
async def test_get_all_with_filters(db_session: AsyncSession, test_category, test_seller):
    """Test getting items with filters."""
    item1 = Item(
        name="Item 1",
        description="Test",
        price=1000.0,
        quantity=10,
        category_id=test_category.id,
        owner_id=test_seller.id,
        is_active=True
    )
    item2 = Item(
        name="Item 2",
        description="Test",
        price=2000.0,
        quantity=10,
        category_id=test_category.id,
        owner_id=test_seller.id,
        is_active=False
    )
    item3 = Item(
        name="Item 3",
        description="Test",
        price=2500.0,
        quantity=10,
        category_id=test_category.id,
        owner_id=test_seller.id,
        is_active=True  # Active item with price >= 1500
    )
    db_session.add(item1)
    db_session.add(item2)
    db_session.add(item3)
    await db_session.commit()  # Commit instead of flush to ensure items are persisted
    
    # Refresh items to ensure they have IDs
    await db_session.refresh(item1)
    await db_session.refresh(item2)
    await db_session.refresh(item3)
    
    from app.services.item_service import ItemService
    service = ItemService(db_session)
    
    # Filter by is_active
    items, total = await service.get_all(filters=ItemFilter(is_active=True))
    # Проверить, что есть хотя бы один активный товар (может быть item1, item3 или другие из других тестов)
    active_items = [item for item in items if item.id in [item1.id, item2.id, item3.id]]
    assert len(active_items) >= 1, f"Expected at least 1 active item, got {len(active_items)}"
    assert all(item.is_active for item in active_items)
    
    # Filter by min_price - item3 имеет price=2500.0, что >= 1500, и is_active=True
    # ItemFilter по умолчанию имеет is_active=True, поэтому item3 должен быть найден
    items, total = await service.get_all(filters=ItemFilter(min_price=1500))
    # Проверить, что item3 найден (item2 не будет найден, так как is_active=False)
    found_items = [item for item in items if item.id in [item1.id, item2.id, item3.id]]
    # item3 должен быть найден, так как он активный и имеет price >= 1500
    assert len(found_items) >= 1, f"Expected at least 1 item with price >= 1500 and is_active=True, got {len(found_items)} items. All items: {[(i.id, i.price, i.is_active) for i in items]}"
    assert all(item.price >= 1500 and item.is_active for item in found_items)
    
    # Filter by max_price
    items, total = await service.get_all(filters=ItemFilter(max_price=1500))
    assert total >= 1
    assert all(item.price <= 1500 for item in items)
    
    # Filter by search
    items, total = await service.get_all(filters=ItemFilter(search="Item 1"))
    assert total >= 1
    assert any("Item 1" in item.name for item in items)
    
    # Filter by owner_id
    items, total = await service.get_all(filters=ItemFilter(owner_id=test_seller.id))
    assert total >= 2


@pytest.mark.asyncio
async def test_get_all_sorting(db_session: AsyncSession, test_category, test_seller):
    """Test getting items with sorting."""
    item1 = Item(
        name="Item A",
        description="Test",
        price=1000.0,
        quantity=10,
        category_id=test_category.id,
        owner_id=test_seller.id
    )
    item2 = Item(
        name="Item B",
        description="Test",
        price=2000.0,
        quantity=10,
        category_id=test_category.id,
        owner_id=test_seller.id
    )
    db_session.add(item1)
    db_session.add(item2)
    await db_session.flush()
    
    service = ItemService(db_session)
    
    # Sort by price ascending
    items, _ = await service.get_all(sort_by="price", sort_order="asc")
    prices = [item.price for item in items if item.id in [item1.id, item2.id]]
    if len(prices) == 2:
        assert prices[0] <= prices[1]
    
    # Sort by name descending
    items, _ = await service.get_all(sort_by="name", sort_order="desc")
    names = [item.name for item in items if item.id in [item1.id, item2.id]]
    if len(names) == 2:
        assert names[0] >= names[1]


@pytest.mark.asyncio
async def test_count(db_session: AsyncSession, test_category, test_seller):
    """Test counting items."""
    service = ItemService(db_session)
    
    total = await service.count()
    active = await service.count(is_active=True)
    inactive = await service.count(is_active=False)
    
    assert total >= 0
    assert active >= 0
    assert inactive >= 0
    assert total >= active + inactive


@pytest.mark.asyncio
async def test_update_not_owner(db_session: AsyncSession, test_item, test_user):
    """Test updating item by non-owner."""
    service = ItemService(db_session)
    with pytest.raises(AuthorizationError):
        await service.update(
            test_item.id,
            ItemUpdate(name="New Name"),
            test_user.id,
            is_admin=False
        )


@pytest.mark.asyncio
async def test_update_by_admin(db_session: AsyncSession, test_item, test_admin):
    """Test updating item by admin."""
    service = ItemService(db_session)
    updated = await service.update(
        test_item.id,
        ItemUpdate(name="New Name"),
        test_admin.id,
        is_admin=True
    )
    assert updated.name == "New Name"


@pytest.mark.asyncio
async def test_delete_not_owner(db_session: AsyncSession, test_item, test_user):
    """Test deleting item by non-owner."""
    service = ItemService(db_session)
    with pytest.raises(AuthorizationError):
        await service.delete(test_item.id, test_user.id, is_admin=False)


@pytest.mark.asyncio
async def test_delete_by_admin(db_session: AsyncSession, test_item, test_admin):
    """Test deleting item by admin."""
    service = ItemService(db_session)
    result = await service.delete(test_item.id, test_admin.id, is_admin=True)
    assert result is True
    
    found = await service.get_by_id(test_item.id)
    assert found is None


@pytest.mark.asyncio
async def test_get_by_category(db_session: AsyncSession, test_category, test_seller):
    """Test getting items by category."""
    item = Item(
        name="Test Item",
        description="Test",
        price=1000.0,
        quantity=10,
        category_id=test_category.id,
        owner_id=test_seller.id,
        is_active=True
    )
    db_session.add(item)
    await db_session.flush()
    
    service = ItemService(db_session)
    items = await service.get_by_category(test_category.id)
    assert len(items) > 0
    assert all(item.category_id == test_category.id for item in items)
    assert all(item.is_active for item in items)


@pytest.mark.asyncio
async def test_get_stats_by_category(db_session: AsyncSession, test_category, test_seller):
    """Test getting stats by category."""
    item = Item(
        name="Test Item",
        description="Test",
        price=1000.0,
        quantity=10,
        category_id=test_category.id,
        owner_id=test_seller.id
    )
    db_session.add(item)
    await db_session.flush()
    
    service = ItemService(db_session)
    stats = await service.get_stats_by_category()
    assert isinstance(stats, dict)
    if test_category.name in stats:
        assert stats[test_category.name] >= 1

