"""Тесты для профиля пользователя."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Category, Item


@pytest.mark.asyncio
async def test_get_profile(client: AsyncClient, auth_headers):
    """Тест получения профиля пользователя."""
    response = await client.get("/api/v1/auth/me/profile", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "user" in data
    assert "created_at" in data
    assert "orders_count" in data
    assert "items_purchased" in data
    assert "role_prefix" in data
    assert data["orders_count"] >= 0
    assert data["items_purchased"] >= 0


@pytest.mark.asyncio
async def test_get_profile_seller_stats(client: AsyncClient, seller_headers, test_item):
    """Тест получения профиля продавца со статистикой товаров."""
    response = await client.get("/api/v1/auth/me/profile", headers=seller_headers)
    assert response.status_code == 200
    data = response.json()
    assert "seller_items_count" in data
    assert data["seller_items_count"] >= 0


@pytest.mark.asyncio
async def test_get_profile_unauthorized(client: AsyncClient):
    """Тест получения профиля без авторизации."""
    response = await client.get("/api/v1/auth/me/profile")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_password_min_length_8(client: AsyncClient):
    """Тест минимальной длины пароля 8 символов."""
    # Пароль из 7 символов должен быть отклонен
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test7@example.com",
            "username": "testuser7",
            "password": "1234567"  # 7 символов
        }
    )
    assert response.status_code == 422
    
    # Пароль из 8 символов должен быть принят
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test8@example.com",
            "username": "testuser8",
            "password": "12345678"  # 8 символов
        }
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_seller_panel_get_items(client: AsyncClient, seller_headers, test_item):
    """Тест получения товаров продавца."""
    response = await client.get("/api/v1/items/my/items", headers=seller_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) >= 0


@pytest.mark.asyncio
async def test_seller_panel_create_item(client: AsyncClient, seller_headers, test_category):
    """Тест создания товара продавцом."""
    response = await client.post(
        "/api/v1/items",
        headers=seller_headers,
        json={
            "name": "Test Item Seller",
            "description": "Test description",
            "price": 1000.0,
            "quantity": 10,
            "category_id": test_category.id
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Item Seller"
    assert data["price"] == 1000.0


@pytest.mark.asyncio
async def test_seller_panel_update_item(client: AsyncClient, seller_headers, test_item):
    """Тест обновления товара продавцом."""
    response = await client.put(
        f"/api/v1/items/{test_item.id}",
        headers=seller_headers,
        json={
            "name": "Updated Item Name",
            "price": 2000.0
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Item Name"
    assert data["price"] == 2000.0


@pytest.mark.asyncio
async def test_seller_panel_toggle_item_active(client: AsyncClient, seller_headers, test_item):
    """Тест деактивации/активации товара."""
    original_active = test_item.is_active
    
    response = await client.put(
        f"/api/v1/items/{test_item.id}",
        headers=seller_headers,
        json={"is_active": not original_active}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] == (not original_active)


@pytest.mark.asyncio
async def test_admin_edit_item(client: AsyncClient, admin_headers, test_item):
    """Тест редактирования товара админом."""
    response = await client.put(
        f"/api/v1/admin/items/{test_item.id}",
        headers=admin_headers,
        json={
            "name": "Admin Updated Item",
            "description": "Updated by admin",
            "price": 5000.0,
            "quantity": 50
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Admin Updated Item"
    assert data["price"] == 5000.0
    assert data["quantity"] == 50


@pytest.mark.asyncio
async def test_admin_deactivate_item(client: AsyncClient, admin_headers, test_item):
    """Тест деактивации товара админом."""
    response = await client.put(
        f"/api/v1/admin/items/{test_item.id}",
        headers=admin_headers,
        json={"is_active": False}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] is False
    
    # Проверить, что товар не отображается в публичном списке
    response = await client.get("/api/v1/items")
    items = response.json()["items"]
    assert not any(item["id"] == test_item.id for item in items)


@pytest.mark.asyncio
async def test_seller_cannot_edit_other_seller_item(client: AsyncClient, seller_headers, db_session):
    """Тест: продавец не может редактировать товар другого продавца."""
    from app.models import User, Item, Category, UserRole
    from app.core.security import get_password_hash
    
    # Создать второго продавца
    seller2 = User(
        email="seller2@example.com",
        username="seller2",
        password_hash=get_password_hash("seller2123"),
        role=UserRole.SELLER,
        is_active=True
    )
    db_session.add(seller2)
    await db_session.flush()
    
    # Создать категорию
    category = Category(name="Test Category", slug="test-category-2", description="Test")
    db_session.add(category)
    await db_session.flush()
    
    # Создать товар от второго продавца
    item = Item(
        name="Seller2 Item",
        description="Item from seller2",
        price=1000.0,
        quantity=10,
        category_id=category.id,
        owner_id=seller2.id,
        is_active=True
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    
    # Первый продавец пытается редактировать товар второго продавца
    response = await client.put(
        f"/api/v1/items/{item.id}",
        headers=seller_headers,
        json={"name": "Hacked Item"}
    )
    assert response.status_code == 403  # Forbidden


@pytest.mark.asyncio
async def test_seller_cannot_delete_other_seller_item(client: AsyncClient, seller_headers, db_session):
    """Тест: продавец не может удалить товар другого продавца."""
    from app.models import User, Item, Category, UserRole
    from app.core.security import get_password_hash
    
    # Создать второго продавца
    seller2 = User(
        email="seller3@example.com",
        username="seller3",
        password_hash=get_password_hash("seller3123"),
        role=UserRole.SELLER,
        is_active=True
    )
    db_session.add(seller2)
    await db_session.flush()
    
    # Создать категорию
    category = Category(name="Test Category 2", slug="test-category-3", description="Test")
    db_session.add(category)
    await db_session.flush()
    
    # Создать товар от второго продавца
    item = Item(
        name="Seller3 Item",
        description="Item from seller3",
        price=1000.0,
        quantity=10,
        category_id=category.id,
        owner_id=seller2.id,
        is_active=True
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    
    # Первый продавец пытается удалить товар второго продавца
    response = await client.delete(
        f"/api/v1/items/{item.id}",
        headers=seller_headers
    )
    assert response.status_code == 403  # Forbidden


@pytest.mark.asyncio
async def test_seed_items_owned_by_admin(client: AsyncClient, admin_headers, db_session, test_admin, test_category):
    """Тест: товары при seed создаются с owner_id админа."""
    from app.models import Item
    from sqlalchemy import select
    
    # Использовать существующего админа из fixture
    admin = test_admin
    
    # Создать товар для админа
    item = Item(
        name="AMD Ryzen 9 7950X",
        description="16-ядерный процессор",
        price=45990,
        quantity=15,
        category_id=test_category.id,
        owner_id=admin.id
    )
    db_session.add(item)
    await db_session.commit()
    
    # Проверить, что товар принадлежит админу
    result = await db_session.execute(select(Item).where(Item.owner_id == admin.id).limit(5))
    admin_items = result.scalars().all()
    
    assert len(admin_items) > 0, "Admin should have items"
    assert all(item.owner_id == admin.id for item in admin_items)

