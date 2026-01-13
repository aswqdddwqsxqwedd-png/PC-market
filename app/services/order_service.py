from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional, Tuple
from app.models import Order, OrderItem, OrderStatus, CartItem, Item, UserRole
from app.schemas import OrderCreate, OrderStatusUpdate
from app.core.exceptions import NotFoundError, ValidationError, AuthorizationError
from app.services.cart_service import CartService


# Допустимые переходы статусов
STATUS_TRANSITIONS = {
    OrderStatus.PENDING: [OrderStatus.PAID, OrderStatus.CANCELLED],
    OrderStatus.PAID: [OrderStatus.SHIPPED, OrderStatus.CANCELLED, OrderStatus.RETURNED],
    OrderStatus.SHIPPED: [OrderStatus.DELIVERED, OrderStatus.CANCELLED],
    OrderStatus.DELIVERED: [OrderStatus.RETURNED],
    OrderStatus.CANCELLED: [],
    OrderStatus.RETURNED: []
}


class OrderService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.cart_service = CartService(db)
    
    async def get_by_id(self, order_id: int) -> Optional[Order]:
        result = await self.db.execute(
            select(Order)
            .options(
                selectinload(Order.items).selectinload(OrderItem.item)
            )
            .where(Order.id == order_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_orders(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 20,
        status: Optional[OrderStatus] = None
    ) -> Tuple[List[Order], int]:
        query = select(Order).options(
            selectinload(Order.items).selectinload(OrderItem.item)
        ).where(Order.user_id == user_id)
        count_query = select(func.count(Order.id)).where(Order.user_id == user_id)
        
        if status:
            query = query.where(Order.status == status)
            count_query = count_query.where(Order.status == status)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        query = query.order_by(Order.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        orders = list(result.scalars().all())
        
        return orders, total
    
    async def get_all_orders(
        self,
        skip: int = 0,
        limit: int = 20,
        status: Optional[OrderStatus] = None
    ) -> Tuple[List[Order], int]:
        query = select(Order).options(
            selectinload(Order.items).selectinload(OrderItem.item)
        )
        count_query = select(func.count(Order.id))
        
        if status:
            query = query.where(Order.status == status)
            count_query = count_query.where(Order.status == status)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        query = query.order_by(Order.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        orders = list(result.scalars().all())
        
        return orders, total
    
    async def create_from_cart(self, user_id: int, order_data: OrderCreate) -> Order:
        """
        Создать заказ из корзины пользователя.
        
        Args:
            user_id: ID пользователя, создающего заказ
            order_data: Данные для создания заказа (адрес доставки и т.д.)
            
        Returns:
            Созданный заказ с загруженными связями
            
        Raises:
            ValidationError: Если корзина пуста или недостаточно товара на складе
        """
        # Получить элементы корзины
        cart_items = await self.cart_service.get_cart(user_id)
        if not cart_items:
            raise ValidationError("Корзина пуста")
        
        # Рассчитать итог и проверить наличие товара
        total_price = 0
        for cart_item in cart_items:
            if cart_item.item.quantity < cart_item.quantity:
                raise ValidationError(
                    f"Недостаточно товара '{cart_item.item.name}'",
                    {"item": cart_item.item.name, "available": cart_item.item.quantity}
                )
            total_price += cart_item.quantity * cart_item.item.price
        
        # Создать заказ
        order = Order(
            user_id=user_id,
            total_price=total_price,
            status=OrderStatus.PENDING,
            shipping_address=order_data.shipping_address
        )
        self.db.add(order)
        await self.db.flush()
        
        # Создать элементы заказа и обновить склад
        for cart_item in cart_items:
            order_item = OrderItem(
                order_id=order.id,
                item_id=cart_item.item_id,
                quantity=cart_item.quantity,
                price_at_purchase=cart_item.item.price
            )
            self.db.add(order_item)
            
            # Обновить склад
            cart_item.item.quantity -= cart_item.quantity
        
        # Очистить корзину
        await self.cart_service.clear_cart(user_id)
        
        await self.db.flush()
        
        # Перезагрузить заказ со связями, чтобы избежать проблем с ленивой загрузкой
        result = await self.db.execute(
            select(Order)
            .options(
                selectinload(Order.items).selectinload(OrderItem.item)
            )
            .where(Order.id == order.id)
        )
        order = result.scalar_one()
        return order
    
    async def update_status(
        self,
        order_id: int,
        status_data: OrderStatusUpdate,
        user_id: int,
        user_role: UserRole
    ) -> Order:
        order = await self.get_by_id(order_id)
        if not order:
            raise NotFoundError("Order", order_id)
        
        # Проверить права доступа
        if user_role != UserRole.ADMIN and order.user_id != user_id:
            raise AuthorizationError("У вас нет прав для обновления этого заказа")
        
        new_status = status_data.status

        # Для администраторов разрешены любые переходы статусов, кроме перехода в текущий статус
        if user_role == UserRole.ADMIN:
            if new_status == order.status:
                raise ValidationError("Новый статус не может быть таким же, как текущий")
            # Пропускаем проверку STATUS_TRANSITIONS для админов
        else:
            # Для не-админов применяем строгие правила переходов
            allowed_transitions = STATUS_TRANSITIONS.get(order.status, [])
            if new_status not in allowed_transitions:
                raise ValidationError(
                    f"Cannot change status from {order.status.value} to {new_status.value}",
                    {"current": order.status.value, "allowed": [s.value for s in allowed_transitions]}
                )
        
        order.status = new_status
        await self.db.flush()
        
        # Перезагрузить заказ со связями, чтобы избежать проблем с ленивой загрузкой
        result = await self.db.execute(
            select(Order)
            .options(
                selectinload(Order.items).selectinload(OrderItem.item)
            )
            .where(Order.id == order.id)
        )
        order = result.scalar_one()
        return order
    
    async def count(self, status: Optional[OrderStatus] = None) -> int:
        query = select(func.count(Order.id))
        if status:
            query = query.where(Order.status == status)
        result = await self.db.execute(query)
        return result.scalar()
    
    async def get_total_revenue(self) -> float:
        result = await self.db.execute(
            select(func.sum(Order.total_price))
            .where(Order.status.in_([OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.DELIVERED]))
        )
        return result.scalar() or 0.0
    
    async def get_stats_by_status(self) -> dict:
        result = await self.db.execute(
            select(Order.status, func.count(Order.id))
            .group_by(Order.status)
        )
        return {row.status.value: row[1] for row in result}
    
    async def delete(self, order_id: int, is_admin: bool = False) -> bool:
        """
        Удалить заказ.
        
        Args:
            order_id: ID заказа для удаления
            is_admin: Является ли пользователь админом (только админы могут удалять заказы)
            
        Returns:
            True при успешном удалении
            
        Raises:
            NotFoundError: Если заказ не найден
            AuthorizationError: Если пользователь не админ
        """
        if not is_admin:
            raise AuthorizationError("Только админы могут удалять заказы")
        
        order = await self.get_by_id(order_id)
        if not order:
            raise NotFoundError("Order", order_id)
        
        # Удалить заказ (каскадное удаление обработает OrderItems и Messages)
        await self.db.delete(order)
        await self.db.flush()
        return True
