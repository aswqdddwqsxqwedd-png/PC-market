from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional, List
from app.models import User, UserRole
from app.schemas import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password
from app.core.exceptions import NotFoundError, ConflictError, AuthenticationError


class UserService:
    """
    Service for user management operations.
    
    Handles CRUD operations and authentication for users.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize UserService.
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User object or None if not found
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
    
    async def get_by_username(self, username: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None
    ) -> List[User]:
        query = select(User)
        if role:
            query = query.where(User.role == role)
        if is_active is not None:
            query = query.where(User.is_active == is_active)
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def count(
        self,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None
    ) -> int:
        query = select(func.count(User.id))
        if role:
            query = query.where(User.role == role)
        if is_active is not None:
            query = query.where(User.is_active == is_active)
        result = await self.db.execute(query)
        return result.scalar()
    
    async def create(self, user_data: UserCreate) -> User:
        # Check for existing email
        existing = await self.get_by_email(user_data.email)
        if existing:
            raise ConflictError("User", "Email already registered")
        
        # Check for existing username
        existing = await self.get_by_username(user_data.username)
        if existing:
            raise ConflictError("User", "Username already taken")
        
        user = User(
            email=user_data.email,
            username=user_data.username,
            password_hash=get_password_hash(user_data.password),
            role=UserRole.USER
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user
    
    async def update(self, user_id: int, user_data: UserUpdate) -> User:
        user = await self.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)
        
        update_data = user_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(user, key, value)
        
        await self.db.flush()
        await self.db.refresh(user)
        return user
    
    async def delete(self, user_id: int) -> bool:
        user = await self.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)
        
        await self.db.delete(user)
        await self.db.flush()
        return True
    
    async def authenticate(self, identifier: str, password: str) -> User:
        """
        Authenticate user by email or username.
        
        Args:
            identifier: Email or username
            password: User password
            
        Returns:
            Authenticated User object
            
        Raises:
            AuthenticationError: If credentials are invalid or user is inactive
        """
        # Try to find user by email first
        user = await self.get_by_email(identifier)
        
        # If not found by email, try username
        if not user:
            user = await self.get_by_username(identifier)
        
        if not user:
            raise AuthenticationError("Invalid email/username or password")
        
        if not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid email/username or password")
        
        if not user.is_active:
            raise AuthenticationError("User account is deactivated")
        
        return user
