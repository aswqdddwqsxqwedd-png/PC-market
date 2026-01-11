from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
from app.db import get_db
from app.schemas import UserCreate, UserLogin, UserResponse, Token
from app.services import UserService
from app.core.security import create_access_token
from app.core.config import settings
from app.api.deps import get_current_user
from app.models import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user."""
    user_service = UserService(db)
    user = await user_service.create(user_data)
    return user


@router.post("/login", response_model=Token)
async def login(
    user_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """Login and get access token. Can login with email or username."""
    user_service = UserService(db)
    user = await user_service.authenticate(user_data.identifier, user_data.password)
    
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )
    
    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info."""
    return current_user


@router.get("/me/profile")
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получить профиль пользователя со статистикой."""
    from app.services import OrderService, ItemService
    from sqlalchemy import select, func
    from app.models import Order, OrderItem, Item
    
    order_service = OrderService(db)
    item_service = ItemService(db)
    
    # Количество заказов пользователя
    orders_count_result = await db.execute(
        select(func.count(Order.id)).where(Order.user_id == current_user.id)
    )
    orders_count = orders_count_result.scalar() or 0
    
    # Количество купленных товаров (сумма quantity из OrderItem)
    items_count_result = await db.execute(
        select(func.sum(OrderItem.quantity))
        .join(Order)
        .where(Order.user_id == current_user.id)
    )
    items_count = items_count_result.scalar() or 0
    
    # Для селлера: количество товаров
    seller_items_count = 0
    if current_user.role.value in ['seller', 'admin']:
        seller_items_result = await db.execute(
            select(func.count(Item.id)).where(Item.owner_id == current_user.id)
        )
        seller_items_count = seller_items_result.scalar() or 0
    
    # Префикс в зависимости от роли
    role_prefix_map = {
        'admin': 'Админ',
        'seller': 'Продавец',
        'support': 'Поддержка',
        'user': 'Пользователь'
    }
    role_prefix = role_prefix_map.get(current_user.role.value, 'Пользователь')
    
    return {
        "user": current_user,
        "created_at": current_user.created_at,
        "orders_count": orders_count,
        "items_purchased": items_count or 0,
        "seller_items_count": seller_items_count,
        "role_prefix": role_prefix
    }