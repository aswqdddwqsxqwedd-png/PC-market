"""Tests for UserService."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.user_service import UserService
from app.models import User, UserRole
from app.schemas import UserCreate, UserUpdate
from app.core.exceptions import NotFoundError, ConflictError, AuthenticationError


@pytest.mark.asyncio
async def test_get_by_email_not_found(db_session: AsyncSession):
    """Test getting user by non-existent email."""
    service = UserService(db_session)
    user = await service.get_by_email("nonexistent@example.com")
    assert user is None


@pytest.mark.asyncio
async def test_get_by_username_not_found(db_session: AsyncSession):
    """Test getting user by non-existent username."""
    service = UserService(db_session)
    user = await service.get_by_username("nonexistent")
    assert user is None


@pytest.mark.asyncio
async def test_get_all_with_filters(db_session: AsyncSession, test_user, test_admin):
    """Test getting all users with filters."""
    service = UserService(db_session)
    
    # Filter by role
    users = await service.get_all(role=UserRole.USER)
    assert len(users) >= 1
    assert all(user.role == UserRole.USER for user in users)
    
    # Filter by is_active
    users = await service.get_all(is_active=True)
    assert len(users) >= 2
    assert all(user.is_active for user in users)


@pytest.mark.asyncio
async def test_count_with_filters(db_session: AsyncSession, test_user, test_admin):
    """Test counting users with filters."""
    service = UserService(db_session)
    
    total = await service.count()
    users = await service.count(role=UserRole.USER)
    admins = await service.count(role=UserRole.ADMIN)
    active = await service.count(is_active=True)
    
    assert total >= 2
    assert users >= 1
    assert admins >= 1
    assert active >= 2


@pytest.mark.asyncio
async def test_create_user_duplicate_email(db_session: AsyncSession, test_user):
    """Test creating user with duplicate email."""
    service = UserService(db_session)
    user_data = UserCreate(
        email=test_user.email,
        username="different_username",
        password="password123"
    )
    with pytest.raises(ConflictError):
        await service.create(user_data)


@pytest.mark.asyncio
async def test_create_user_duplicate_username(db_session: AsyncSession, test_user):
    """Test creating user with duplicate username."""
    service = UserService(db_session)
    user_data = UserCreate(
        email="different@example.com",
        username=test_user.username,
        password="password123"
    )
    with pytest.raises(ConflictError):
        await service.create(user_data)


@pytest.mark.asyncio
async def test_update_user_not_found(db_session: AsyncSession):
    """Test updating non-existent user."""
    service = UserService(db_session)
    with pytest.raises(NotFoundError):
        await service.update(999, UserUpdate(username="new_username"))


@pytest.mark.asyncio
async def test_delete_user_not_found(db_session: AsyncSession):
    """Test deleting non-existent user."""
    service = UserService(db_session)
    with pytest.raises(NotFoundError):
        await service.delete(999)


@pytest.mark.asyncio
async def test_authenticate_invalid_email(db_session: AsyncSession):
    """Test authentication with invalid email."""
    service = UserService(db_session)
    with pytest.raises(AuthenticationError):
        await service.authenticate("nonexistent@example.com", "password123")


@pytest.mark.asyncio
async def test_authenticate_invalid_password(db_session: AsyncSession, test_user):
    """Test authentication with invalid password."""
    service = UserService(db_session)
    with pytest.raises(AuthenticationError):
        await service.authenticate(test_user.email, "wrong_password")


@pytest.mark.asyncio
async def test_authenticate_inactive_user(db_session: AsyncSession):
    """Test authentication with inactive user."""
    from app.core.security import get_password_hash
    
    user = User(
        email="inactive@example.com",
        username="inactive",
        password_hash=get_password_hash("password123"),
        role=UserRole.USER,
        is_active=False
    )
    db_session.add(user)
    await db_session.flush()
    
    service = UserService(db_session)
    with pytest.raises(AuthenticationError):
        await service.authenticate("inactive@example.com", "password123")

