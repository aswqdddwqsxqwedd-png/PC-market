"""Сервис уведомлений для фоновых задач."""
import structlog
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy import delete, select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import OrderStatus, CartItem, Message, Order

logger = structlog.get_logger(__name__)


async def send_order_status_notification(
    order_id: int,
    user_id: int,
    old_status: Optional[OrderStatus],
    new_status: OrderStatus
) -> None:
    """
    Отправить уведомление об изменении статуса заказа.
    
    Это заглушка для email/push уведомлений.
    В продакшене интегрировать с email-сервисом (SendGrid, AWS SES и т.д.)
    или сервисом push-уведомлений.
    
    Args:
        order_id: ID заказа
        user_id: ID пользователя для уведомления
        old_status: Предыдущий статус заказа
        new_status: Новый статус заказа
    """
    logger.info(
        "order_status_notification",
        order_id=order_id,
        user_id=user_id,
        old_status=old_status.value if old_status else None,
        new_status=new_status.value,
        message=f"Статус заказа #{order_id} изменен на {new_status.value}"
    )
    
    # TODO: Реализовать отправку уведомлений
    # Пример с email:
    # await email_client.send(
    #     to=user.email,
    #     subject=f"Обновление статуса заказа #{order_id}",
    #     body=f"Статус вашего заказа обновлен до {new_status.value}"
    # )


async def cleanup_old_data(db: AsyncSession) -> dict:
    """
    Очистка старых данных (фоновая задача).
    
    Выполняет следующие операции очистки:
    - Удаление старых элементов корзины (старше 30 дней)
    - Удаление решенных сообщений старше 90 дней
    - Архивация старых отмененных заказов (старше 1 года)
    
    Args:
        db: Сессия базы данных
        
    Returns:
        Словарь со статистикой очистки
    """
    logger.info("cleanup_old_data_started")
    stats = {
        "cart_items_deleted": 0,
        "messages_deleted": 0,
        "orders_archived": 0
    }
    
    try:
        # 1. Удалить старые элементы корзины (старше 30 дней)
        cart_cutoff = datetime.utcnow() - timedelta(days=30)
        cart_result = await db.execute(
            delete(CartItem).where(CartItem.added_at < cart_cutoff)
        )
        stats["cart_items_deleted"] = cart_result.rowcount
        logger.info("cleanup_cart_items", deleted=stats["cart_items_deleted"])
        
        # 2. Удалить решенные сообщения старше 90 дней
        messages_cutoff = datetime.utcnow() - timedelta(days=90)
        messages_result = await db.execute(
            delete(Message).where(
                and_(
                    Message.is_resolved == True,
                    Message.created_at < messages_cutoff
                )
            )
        )
        stats["messages_deleted"] = messages_result.rowcount
        logger.info("cleanup_messages", deleted=stats["messages_deleted"])
        
        # 3. Архивировать старые отмененные заказы (старше 1 года)
        # Пока просто логируем их. В продакшене можно переместить в архивную таблицу
        orders_cutoff = datetime.utcnow() - timedelta(days=365)
        orders_result = await db.execute(
            select(func.count(Order.id)).where(
                and_(
                    Order.status == OrderStatus.CANCELLED,
                    Order.created_at < orders_cutoff
                )
            )
        )
        old_cancelled_count = orders_result.scalar() or 0
        stats["orders_archived"] = old_cancelled_count
        logger.info("cleanup_orders", old_cancelled_orders=old_cancelled_count)
        
        await db.commit()
        logger.info("cleanup_old_data_completed", stats=stats)
        
    except Exception as e:
        await db.rollback()
        logger.error("cleanup_old_data_error", error=str(e), exc_info=True)
        raise
    
    return stats

