from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.db import get_db
from app.schemas import (
    OrderCreate, OrderStatusUpdate, OrderResponse, 
    OrderDetailResponse, OrderListResponse
)
from app.services import OrderService
from app.api.deps import get_current_user
from app.models import User, OrderStatus

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.get("", response_model=OrderListResponse)
async def get_my_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[OrderStatus] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's orders."""
    service = OrderService(db)
    skip = (page - 1) * limit
    orders, total = await service.get_user_orders(current_user.id, skip, limit, status)
    
    pages = (total + limit - 1) // limit
    
    return OrderListResponse(
        orders=orders,
        total=total,
        page=page,
        pages=pages
    )


@router.get("/{order_id}", response_model=OrderDetailResponse)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get order by ID."""
    service = OrderService(db)
    order = await service.get_by_id(order_id)
    
    if not order:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Order", order_id)
    
    # Check ownership (admin can see all)
    from app.models import UserRole
    if order.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        from app.core.exceptions import AuthorizationError
        raise AuthorizationError("You don't have permission to view this order")
    
    return order


@router.post("", response_model=OrderDetailResponse, status_code=201)
async def create_order(
    order_data: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create order from cart."""
    service = OrderService(db)
    order = await service.create_from_cart(current_user.id, order_data)
    return order


@router.put("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: int,
    status_data: OrderStatusUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update order status.
    
    Args:
        order_id: Order ID
        status_data: New status data
        background_tasks: FastAPI background tasks
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Updated order
    """
    service = OrderService(db)
    order = await service.update_status(
        order_id, status_data, current_user.id, current_user.role
    )
    
    # Send notification in background
    from app.services.notification_service import send_order_status_notification as notify
    background_tasks.add_task(
        notify,
        order_id=order.id,
        user_id=order.user_id,
        old_status=None,  # Could be retrieved if needed
        new_status=order.status
    )
    
    return order
