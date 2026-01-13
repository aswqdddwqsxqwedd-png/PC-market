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

# Shared async engine with StaticPool so the same in-memory DB is reused
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False
)


_tables_created = False


@pytest.fixture(scope="function")
async def _setup_db():
    """Ensure tables exist once (function scope to satisfy event_loop fixture)."""
    global _tables_created
    if not _tables_created:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        _tables_created = True
    yield


@pytest.fixture(scope="function")
async def db_session(_setup_db) -> AsyncGenerator[AsyncSession, None]:
    """
    Fast per-test session using a single in-memory DB with rollback.
    
    Uses one engine with StaticPool and wraps each test in a transaction
    that is rolled back to isolate state without recreating tables.
    """
    async with test_engine.connect() as connection:
        trans = await connection.begin()
        session = AsyncSession(bind=connection, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()


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
    """Create a test user - optimized with flush instead of commit."""
    user = User(
        email="test@example.com",
        username="testuser",
        password_hash=get_password_hash("testpass123"),
        role=UserRole.USER,
        is_active=True
    )
    db_session.add(user)
    await db_session.flush()  # Faster than commit, gets ID immediately
    return user


@pytest.fixture
async def test_seller(db_session: AsyncSession) -> User:
    """Create a test seller - optimized with flush instead of commit."""
    seller = User(
        email="seller@example.com",
        username="seller",
        password_hash=get_password_hash("seller123"),
        role=UserRole.SELLER,
        is_active=True
    )
    db_session.add(seller)
    await db_session.flush()  # Faster than commit, gets ID immediately
    return seller


@pytest.fixture
async def test_admin(db_session: AsyncSession) -> User:
    """Create a test admin - optimized with flush instead of commit."""
    admin = User(
        email="admin@example.com",
        username="admin",
        password_hash=get_password_hash("admin123"),
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(admin)
    await db_session.flush()  # Faster than commit, gets ID immediately
    return admin


@pytest.fixture
async def auth_headers(test_user: User) -> dict:
    """Get authentication headers for test user - fast token creation."""
    # Create token directly - much faster than HTTP login
    from app.core.security import create_access_token
    token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def seller_headers(test_seller: User) -> dict:
    """Get authentication headers for test seller - fast token creation."""
    from app.core.security import create_access_token
    token = create_access_token(data={"sub": str(test_seller.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def admin_headers(test_admin: User) -> dict:
    """Get authentication headers for test admin - fast token creation."""
    from app.core.security import create_access_token
    token = create_access_token(data={"sub": str(test_admin.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def test_support(db_session: AsyncSession) -> User:
    """Create a test support user - optimized with flush instead of commit."""
    support = User(
        email="support@example.com",
        username="support",
        password_hash=get_password_hash("support123"),
        role=UserRole.SUPPORT,
        is_active=True
    )
    db_session.add(support)
    await db_session.flush()  # Faster than commit, gets ID immediately
    return support


@pytest.fixture
async def support_headers(test_support: User) -> dict:
    """Get authentication headers for test support user - fast token creation."""
    from app.core.security import create_access_token
    token = create_access_token(data={"sub": str(test_support.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def test_category(db_session: AsyncSession):
    """Create a test category - optimized with flush instead of commit."""
    from app.models import Category
    category = Category(
        name="Тестовая категория",
        slug="test-category",
        description="Описание категории"
    )
    db_session.add(category)
    await db_session.flush()  # Faster than commit, gets ID immediately
    return category


@pytest.fixture
async def test_item(db_session: AsyncSession, test_seller, test_category):
    """Create a test item - optimized with flush instead of commit."""
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
    await db_session.flush()  # Faster than commit, gets ID immediately
    return item

