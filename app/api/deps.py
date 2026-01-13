from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.db import get_db
from app.models import User, UserRole
from app.core.security import decode_token
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.services import UserService

security = HTTPBearer()


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current authenticated user.
    
    Args:
        request: FastAPI request object
        credentials: HTTP Bearer token credentials
        db: Database session
        
    Returns:
        Authenticated User object
        
    Raises:
        AuthenticationError: If token is invalid or user not found
    """
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload is None:
        raise AuthenticationError("Invalid token")
    
    user_id = payload.get("sub")
    if user_id is None:
        raise AuthenticationError("Invalid token payload")
    
    user_service = UserService(db)
    user = await user_service.get_by_id(int(user_id))
    
    if user is None:
        raise AuthenticationError("User not found")
    
    if not user.is_active:
        raise AuthenticationError("User account is deactivated")
    
    # Store user_id in request state for middleware
    request.state.user_id = user.id
    
    return user


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise.
    
    Args:
        request: FastAPI request object
        credentials: Optional HTTP Bearer token credentials
        db: Database session
        
    Returns:
        User object if authenticated, None otherwise
    """
    if credentials is None:
        return None
    
    try:
        return await get_current_user(request, credentials, db)
    except AuthenticationError:
        return None


class RoleChecker:
    """Dependency for checking user roles."""
    
    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles
    
    async def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise AuthorizationError(
                f"Role '{current_user.role.value}' is not allowed. Required: {[r.value for r in self.allowed_roles]}"
            )
        return current_user


# Convenience dependencies
async def get_current_admin_user(
    current_user: User = Depends(RoleChecker([UserRole.ADMIN]))
) -> User:
    """Get current user with admin role."""
    return current_user


async def get_current_seller_or_admin(
    current_user: User = Depends(RoleChecker([UserRole.SELLER, UserRole.ADMIN]))
) -> User:
    """Get current user with seller or admin role."""
    return current_user
