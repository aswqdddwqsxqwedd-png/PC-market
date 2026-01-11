"""Pytest configuration and fixtures."""
import os
# Set testing environment variable to increase rate limits
os.environ["TESTING"] = "1"

import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.core.config import settings
from app.models import User, UserRole
from app.core.security import get_password_hash
from httpx import AsyncClient, ASGITransport


# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()
    
    # Drop tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client."""
    # Override get_db dependency
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        username="testuser",
        password_hash=get_password_hash("testpass123"),
        role=UserRole.USER,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_seller(db_session: AsyncSession) -> User:
    """Create a test seller."""
    seller = User(
        email="seller@example.com",
        username="seller",
        password_hash=get_password_hash("seller123"),
        role=UserRole.SELLER,
        is_active=True
    )
    db_session.add(seller)
    await db_session.commit()
    await db_session.refresh(seller)
    return seller


@pytest.fixture
async def test_admin(db_session: AsyncSession) -> User:
    """Create a test admin."""
    admin = User(
        email="admin@example.com",
        username="admin",
        password_hash=get_password_hash("admin123"),
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest.fixture
async def auth_headers(client: AsyncClient, test_user: User) -> dict:
    """Get authentication headers for test user."""
    import asyncio
    # Handle rate limiting
    for attempt in range(3):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "testpass123"}
        )
        if response.status_code == 200:
            token = response.json()["access_token"]
            return {"Authorization": f"Bearer {token}"}
        elif response.status_code == 429:
            await asyncio.sleep(1)  # Wait before retry
        else:
            break
    # Fallback: create token directly if login fails
    from app.core.security import create_access_token
    token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def seller_headers(client: AsyncClient, test_seller: User) -> dict:
    """Get authentication headers for test seller."""
    import asyncio
    # Handle rate limiting
    for attempt in range(3):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": test_seller.email, "password": "seller123"}
        )
        if response.status_code == 200:
            token = response.json()["access_token"]
            return {"Authorization": f"Bearer {token}"}
        elif response.status_code == 429:
            await asyncio.sleep(1)  # Wait before retry
        else:
            break
    # Fallback: create token directly if login fails
    from app.core.security import create_access_token
    token = create_access_token(data={"sub": str(test_seller.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def admin_headers(client: AsyncClient, test_admin: User) -> dict:
    """Get authentication headers for test admin."""
    import asyncio
    # Handle rate limiting
    for attempt in range(3):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": test_admin.email, "password": "admin123"}
        )
        if response.status_code == 200:
            token = response.json()["access_token"]
            return {"Authorization": f"Bearer {token}"}
        elif response.status_code == 429:
            await asyncio.sleep(1)  # Wait before retry
        else:
            break
    # Fallback: create token directly if login fails
    from app.core.security import create_access_token
    token = create_access_token(data={"sub": str(test_admin.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def test_support(db_session: AsyncSession) -> User:
    """Create a test support user."""
    support = User(
        email="support@example.com",
        username="support",
        password_hash=get_password_hash("support123"),
        role=UserRole.SUPPORT,
        is_active=True
    )
    db_session.add(support)
    await db_session.commit()
    await db_session.refresh(support)
    return support


@pytest.fixture
async def support_headers(client: AsyncClient, test_support: User) -> dict:
    """Get authentication headers for test support user."""
    import asyncio
    # Handle rate limiting
    for attempt in range(3):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": test_support.email, "password": "support123"}
        )
        if response.status_code == 200:
            token = response.json()["access_token"]
            return {"Authorization": f"Bearer {token}"}
        elif response.status_code == 429:
            await asyncio.sleep(1)  # Wait before retry
        else:
            break
    # Fallback: create token directly if login fails
    from app.core.security import create_access_token
    token = create_access_token(data={"sub": str(test_support.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def test_category(db_session: AsyncSession):
    """Create a test category."""
    from app.models import Category
    category = Category(
        name="Тестовая категория",
        slug="test-category",
        description="Описание категории"
    )
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    return category


@pytest.fixture
async def test_item(db_session: AsyncSession, test_seller, test_category):
    """Create a test item."""
    from app.models import Item
    item = Item(
        name="Test Item",
        description="Test description",
        price=1000.0,
        quantity=10,
        category_id=test_category.id,
        owner_id=test_seller.id,
        is_active=True
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    return item

