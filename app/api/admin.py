from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import datetime, timedelta
from app.db import get_db
from app.schemas import (
    UserResponse, UserUpdate, UserWithStats,
    CategoryResponse, CategoryCreate, CategoryUpdate,
    ItemResponse, ItemUpdate, ItemListResponse, ItemFilter,
    OrderResponse, OrderListResponse, OrderStatusUpdate,
    DashboardStats, UserStats, ItemStats, OrderStats
)
from app.schemas.user import AdminUserCreate
from app.schemas.item import ItemCreate
from app.services import UserService, CategoryService, ItemService, OrderService
from app.services.report_service import ReportService
from app.api.deps import get_current_admin_user
from app.models import User, UserRole, Category, Item, Order, OrderStatus
from app.schemas.reports import (
    ActiveUsersReport, ItemsReport, CategoriesReport, SalesReport
)

router = APIRouter(prefix="/admin", tags=["Admin"])


# Эндпоинты отчетов
@router.get("/reports/users", response_model=ActiveUsersReport)
async def get_users_report(
    days: int = Query(30, ge=1, le=365, description="Количество дней для анализа"),
    role: Optional[UserRole] = Query(None, description="Фильтр по роли пользователя"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Получить отчет по активным пользователям.
    
    Предоставляет статистику по активности пользователей, новым регистрациям и топ пользователям.
    
    Args:
        days: Количество дней для анализа (по умолчанию: 30)
        role: Опциональный фильтр по роли
        db: Сессия базы данных
        current_user: Текущий пользователь-админ
        
    Returns:
        ActiveUsersReport со статистикой пользователей
    """
    service = ReportService(db)
    return await service.get_active_users_report(days=days, role=role)


@router.get("/reports/items", response_model=ItemsReport)
async def get_items_report(
    category_id: Optional[int] = Query(None, description="Фильтр по ID категории"),
    days: int = Query(30, ge=1, le=365, description="Количество дней для анализа"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Получить отчет по товарам и продажам.
    
    Предоставляет статистику по товарам, продажам, доходам и топ продающимся товарам.
    
    Args:
        category_id: Опциональный фильтр по категории
        days: Количество дней для анализа (по умолчанию: 30)
        db: Сессия базы данных
        current_user: Текущий пользователь-админ
        
    Returns:
        ItemsReport со статистикой товаров
    """
    service = ReportService(db)
    return await service.get_items_report(category_id=category_id, days=days)


@router.get("/reports/categories", response_model=CategoriesReport)
async def get_categories_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Получить отчет по популярности категорий.
    
    Предоставляет статистику по категориям, их популярности и доходам.
    
    Args:
        db: Сессия базы данных
        current_user: Текущий пользователь-админ
        
    Returns:
        CategoriesReport со статистикой категорий
    """
    service = ReportService(db)
    return await service.get_categories_report()


@router.get("/reports/sales", response_model=SalesReport)
async def get_sales_report(
    days: int = Query(30, ge=1, le=365, description="Количество дней для анализа"),
    status: Optional[OrderStatus] = Query(None, description="Фильтр по статусу заказа"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Получить отчет по продажам.
    
    Предоставляет статистику по заказам, доходам и продажам по статусам.
    
    Args:
        days: Количество дней для анализа (по умолчанию: 30)
        status: Опциональный фильтр по статусу заказа
        db: Сессия базы данных
        current_user: Текущий пользователь-админ
        
    Returns:
        SalesReport со статистикой продаж
    """
    service = ReportService(db)
    return await service.get_sales_report(days=days, status=status)


# ==================== Панель управления ====================

@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Получить статистику панели управления."""
    user_service = UserService(db)
    category_service = CategoryService(db)
    item_service = ItemService(db)
    order_service = OrderService(db)
    
    total_users = await user_service.count()
    total_items = await item_service.count()
    total_orders = await order_service.count()
    total_categories = await category_service.count()
    total_revenue = await order_service.get_total_revenue()
    active_items = await item_service.count(is_active=True)
    
    # Недавние заказы (последние 7 дней)
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_query = select(func.count(Order.id)).where(Order.created_at >= week_ago)
    result = await db.execute(recent_query)
    recent_orders = result.scalar()
    
    return DashboardStats(
        total_users=total_users,
        total_items=total_items,
        total_orders=total_orders,
        total_categories=total_categories,
        total_revenue=total_revenue,
        recent_orders=recent_orders,
        active_items=active_items
    )


# ==================== Управление пользователями ====================

@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Получить всех пользователей (только для админов)."""
    service = UserService(db)
    users = await service.get_all(skip, limit, role, is_active)
    return users


@router.get("/users/stats", response_model=UserStats)
async def get_users_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Получить статистику пользователей."""
    service = UserService(db)

    total = await service.count()
    active = await service.count(is_active=True)

    # Новые сегодня
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    new_today_query = select(func.count(User.id)).where(User.created_at >= today)
    result = await db.execute(new_today_query)
    new_today = result.scalar()

    # По ролям
    by_role = {}
    for role in UserRole:
        count = await service.count(role=role)
        by_role[role.value] = count
    
    return UserStats(
        total=total,
        active=active,
        new_today=new_today,
        by_role=by_role
    )


@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: AdminUserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Создать пользователя (только для админов)."""
    from app.core.security import get_password_hash
    
    service = UserService(db)
    # Проверить, существует ли email
    existing = await service.get_by_email(user_data.email)
    if existing:
        from app.core.exceptions import ConflictError
        raise ConflictError("User", "Email уже зарегистрирован")
    
    # Проверить, существует ли имя пользователя
    existing = await service.get_by_username(user_data.username)
    if existing:
        from app.core.exceptions import ConflictError
        raise ConflictError("User", "Имя пользователя уже занято")
    
    # Создать пользователя с ролью
    user = User(
        email=user_data.email,
        username=user_data.username,
        password_hash=get_password_hash(user_data.password),
        role=user_data.role,
        is_active=user_data.is_active
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Получить пользователя по ID."""
    service = UserService(db)
    user = await service.get_by_id(user_id)
    if not user:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("User", user_id)
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Обновить пользователя (только для админов)."""
    service = UserService(db)
    user = await service.update(user_id, user_data)
    return user


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Удалить пользователя (только для админов)."""
    if user_id == current_user.id:
        from app.core.exceptions import ValidationError
        raise ValidationError("Нельзя удалить самого себя")
    
    service = UserService(db)
    await service.delete(user_id)
    return {"message": "User deleted successfully"}


# ==================== Управление товарами ====================

@router.get("/items", response_model=ItemListResponse)
async def get_all_items(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    category_id: Optional[int] = None,
    owner_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Получить все товары (только для админов)."""
    service = ItemService(db)
    filters = ItemFilter(
        category_id=category_id,
        owner_id=owner_id,
        is_active=is_active,
        search=search
    )
    
    skip = (page - 1) * limit
    items, total = await service.get_all(skip, limit, filters)
    pages = (total + limit - 1) // limit
    
    return ItemListResponse(
        items=items,
        total=total,
        page=page,
        pages=pages,
        has_next=page < pages,
        has_prev=page > 1
    )


@router.get("/items/stats", response_model=ItemStats)
async def get_items_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Получить статистику товаров."""
    service = ItemService(db)

    total = await service.count()
    active = await service.count(is_active=True)
    by_category = await service.get_stats_by_category()

    # Средняя цена
    avg_query = select(func.avg(Item.price))
    result = await db.execute(avg_query)
    avg_price = result.scalar() or 0
    
    return ItemStats(
        total=total,
        active=active,
        by_category=by_category,
        avg_price=round(avg_price, 2)
    )


@router.post("/items", response_model=ItemResponse)
async def admin_create_item(
    item_data: ItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Создать товар (только для админов)."""
    service = ItemService(db)
    # Админ может создавать товары для любого пользователя, но используем current_user.id как владельца
    # Или можно добавить owner_id в схему ItemCreate - пока используем current_user
    item = await service.create(item_data, current_user.id)
    return item


@router.put("/items/{item_id}", response_model=ItemResponse)
async def admin_update_item(
    item_id: int,
    item_data: ItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Обновить любой товар (только для админов)."""
    service = ItemService(db)
    item = await service.update(item_id, item_data, current_user.id, is_admin=True)
    return item


@router.delete("/items/{item_id}")
async def admin_delete_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Удалить любой товар (только для админов)."""
    service = ItemService(db)
    await service.delete(item_id, current_user.id, is_admin=True)
    return {"message": "Item deleted successfully"}


# ==================== Управление заказами ====================

@router.get("/orders", response_model=OrderListResponse)
async def get_all_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[OrderStatus] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Получить все заказы (только для админов)."""
    service = OrderService(db)
    skip = (page - 1) * limit
    orders, total = await service.get_all_orders(skip, limit, status)
    pages = (total + limit - 1) // limit
    
    return OrderListResponse(
        orders=orders,
        total=total,
        page=page,
        pages=pages
    )


@router.get("/orders/stats", response_model=OrderStats)
async def get_orders_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Получить статистику заказов."""
    service = OrderService(db)

    total = await service.count()
    by_status = await service.get_stats_by_status()
    total_revenue = await service.get_total_revenue()

    # Средняя стоимость заказа
    avg_query = select(func.avg(Order.total_price))
    result = await db.execute(avg_query)
    avg_order_value = result.scalar() or 0
    
    return OrderStats(
        total=total,
        by_status=by_status,
        total_revenue=total_revenue,
        avg_order_value=round(avg_order_value, 2)
    )


@router.delete("/orders/{order_id}")
async def admin_delete_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Удалить заказ (только для админов)."""
    service = OrderService(db)
    await service.delete(order_id, is_admin=True)
    return {"message": "Order deleted successfully"}


@router.put("/orders/{order_id}/status", response_model=OrderResponse)
async def admin_update_order_status(
    order_id: int,
    status_data: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Обновить статус заказа (только для админов)."""
    service = OrderService(db)
    order = await service.update_status(
        order_id, status_data, current_user.id, UserRole.ADMIN
    )
    return order


# ==================== Управление категориями ====================

@router.get("/categories", response_model=List[CategoryResponse])
async def admin_get_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Получить все категории."""
    service = CategoryService(db)
    return await service.get_all()


@router.post("/categories", response_model=CategoryResponse, status_code=201)
async def admin_create_category(
    category_data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Создать категорию (только для админов)."""
    service = CategoryService(db)
    return await service.create(category_data)


@router.put("/categories/{category_id}", response_model=CategoryResponse)
async def admin_update_category(
    category_id: int,
    category_data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Обновить категорию (только для админов)."""
    service = CategoryService(db)
    return await service.update(category_id, category_data)


@router.delete("/categories/{category_id}")
async def admin_delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Удалить категорию (только для админов)."""
    service = CategoryService(db)
    await service.delete(category_id)
    return {"message": "Category deleted successfully"}
