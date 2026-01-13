"""Сервис для операций с чатом."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from typing import List, Optional, Tuple
from datetime import datetime
from app.models import Message, User, Order, OrderItem, UserRole
from app.core.exceptions import NotFoundError, AuthorizationError
from app.schemas.chat import MessageCreate


class ChatService:
    """
    Сервис для операций с чатом и сообщениями.
    
    Обрабатывает отправку сообщений, получение истории чата и управление беседами.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Инициализировать ChatService.
        
        Args:
            db: Сессия базы данных
        """
        self.db = db
    
    async def send_message(
        self,
        sender_id: int,
        receiver_id: int,
        text: str,
        order_id: Optional[int] = None,
        item_id: Optional[int] = None
    ) -> Message:
        """
        Отправить сообщение от отправителя получателю.
        
        Args:
            sender_id: ID отправителя сообщения
            receiver_id: ID получателя сообщения
            text: Текст сообщения
            order_id: Опциональный ID заказа, если сообщение связано с заказом
            item_id: Опциональный ID товара, если сообщение связано с товаром
            
        Returns:
            Созданный объект Message
            
        Raises:
            NotFoundError: Если получатель не найден
        """
        # Проверить, существует ли получатель
        receiver = await self.db.execute(select(User).where(User.id == receiver_id))
        receiver = receiver.scalar_one_or_none()
        if not receiver:
            raise NotFoundError("User", receiver_id)
        
        # Если указан order_id, проверить существование заказа и доступ пользователя
        if order_id:
            order = await self.db.execute(
                select(Order).where(Order.id == order_id)
            )
            order = order.scalar_one_or_none()
            if not order:
                raise NotFoundError("Order", order_id)
        
        message = Message(
            sender_id=sender_id,
            receiver_id=receiver_id,
            text=text,
            order_id=order_id,
            item_id=item_id
        )
        self.db.add(message)
        await self.db.flush()
        await self.db.refresh(message)
        
        # Загрузить связи
        result = await self.db.execute(
            select(Message)
            .options(
                selectinload(Message.sender),
                selectinload(Message.receiver),
                selectinload(Message.order)
            )
            .where(Message.id == message.id)
        )
        message = result.scalar_one()
        
        return message
    
    async def get_conversation(
        self,
        user1_id: int,
        user2_id: int,
        order_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[Message], int]:
        """
        Get conversation between two users.
        
        Args:
            user1_id: First user ID
            user2_id: Second user ID
            order_id: Optional order ID to filter by
            skip: Number of messages to skip
            limit: Maximum number of messages to return
            
        Returns:
            Tuple of (messages list, total count)
        """
        query = select(Message).where(
            or_(
                and_(Message.sender_id == user1_id, Message.receiver_id == user2_id),
                and_(Message.sender_id == user2_id, Message.receiver_id == user1_id)
            )
        )
        
        if order_id:
            query = query.where(Message.order_id == order_id)
        
        # Получить общее количество
        total_result = await self.db.execute(
            select(func.count(Message.id)).where(
                or_(
                    and_(Message.sender_id == user1_id, Message.receiver_id == user2_id),
                    and_(Message.sender_id == user2_id, Message.receiver_id == user1_id)
                )
            )
        )
        if order_id:
            total_result = await self.db.execute(
                select(func.count(Message.id)).where(
                    and_(
                        or_(
                            and_(Message.sender_id == user1_id, Message.receiver_id == user2_id),
                            and_(Message.sender_id == user2_id, Message.receiver_id == user1_id)
                        ),
                        Message.order_id == order_id
                    )
                )
            )
        total = total_result.scalar()
        
        # Получить сообщения с пагинацией
        query = query.options(
            selectinload(Message.sender),
            selectinload(Message.receiver),
            selectinload(Message.order)
        ).order_by(Message.created_at.desc()).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        messages = list(result.scalars().all())
        messages.reverse()  # Перевернуть, чтобы показать старые первыми
        
        return messages, total
    
    async def get_user_conversations(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[dict], int]:
        """
        Получить все беседы пользователя (список пользователей, с которыми он общался).
        
        Args:
            user_id: ID пользователя
            skip: Количество бесед для пропуска
            limit: Максимальное количество бесед для возврата
            
        Returns:
            Кортеж (список бесед, общее количество)
        """
        # Получить уникальных партнеров по беседам с временем последнего сообщения
        # Получить отправленные сообщения
        sent_result = await self.db.execute(
            select(
                Message.receiver_id.label("partner_id"),
                func.max(Message.created_at).label("last_message_at")
            )
            .where(Message.sender_id == user_id)
            .group_by(Message.receiver_id)
        )
        sent_partners = {row.partner_id: row.last_message_at for row in sent_result.all()}
        
        # Получить полученные сообщения
        received_result = await self.db.execute(
            select(
                Message.sender_id.label("partner_id"),
                func.max(Message.created_at).label("last_message_at")
            )
            .where(Message.receiver_id == user_id)
            .group_by(Message.sender_id)
        )
        received_partners = {row.partner_id: row.last_message_at for row in received_result.all()}
        
        # Объединить и получить время последнего сообщения для каждого партнера
        all_partners = set(sent_partners.keys()) | set(received_partners.keys())
        partner_times = {}
        for partner_id in all_partners:
            sent_time = sent_partners.get(partner_id)
            received_time = received_partners.get(partner_id)
            if sent_time and received_time:
                partner_times[partner_id] = max(sent_time, received_time)
            elif sent_time:
                partner_times[partner_id] = sent_time
            else:
                partner_times[partner_id] = received_time
        
        # Сортировать по времени последнего сообщения
        sorted_partners = sorted(partner_times.items(), key=lambda x: x[1], reverse=True)
        total = len(sorted_partners)
        
        # Применить пагинацию
        paginated_partners = sorted_partners[skip:skip + limit]
        
        # Получить последнее сообщение для каждой беседы
        conversations = []
        for partner_id, _ in paginated_partners:
            last_message = await self.db.execute(
                select(Message)
                .options(selectinload(Message.sender), selectinload(Message.receiver))
                .where(
                    or_(
                        and_(Message.sender_id == user_id, Message.receiver_id == partner_id),
                        and_(Message.sender_id == partner_id, Message.receiver_id == user_id)
                    )
                )
                .order_by(Message.created_at.desc())
                .limit(1)
            )
            last_message = last_message.scalar_one_or_none()
            
            # Получить пользователя-партнера
            partner = await self.db.execute(select(User).where(User.id == partner_id))
            partner = partner.scalar_one()
            
            conversations.append({
                "partner": partner,
                "last_message": last_message,
                "unread_count": await self._get_unread_count(user_id, partner_id)
            })
        
        return conversations, total
    
    async def _get_unread_count(self, user_id: int, partner_id: int) -> int:
        """Получить количество непрочитанных сообщений от партнера."""
        result = await self.db.execute(
            select(func.count(Message.id)).where(
                and_(
                    Message.sender_id == partner_id,
                    Message.receiver_id == user_id,
                    Message.is_read == False
                )
            )
        )
        return result.scalar() or 0
    
    async def mark_as_read(
        self,
        message_ids: List[int],
        user_id: int
    ) -> int:
        """
        Отметить сообщения как прочитанные.
        
        Args:
            message_ids: Список ID сообщений для отметки как прочитанные
            user_id: ID пользователя, отмечающего сообщения как прочитанные (должен быть получателем)
            
        Returns:
            Количество отмеченных как прочитанные сообщений
        """
        result = await self.db.execute(
            select(Message).where(
                and_(
                    Message.id.in_(message_ids),
                    Message.receiver_id == user_id
                )
            )
        )
        messages = result.scalars().all()
        
        count = 0
        for message in messages:
            message.is_read = True
            count += 1
        
        await self.db.flush()
        return count
    
    async def get_order_chat(
        self,
        order_id: int,
        user_id: int,
        user_role: UserRole
    ) -> List[Message]:
        """
        Получить сообщения чата для конкретного заказа.
        
        Args:
            order_id: ID заказа
            user_id: ID текущего пользователя
            user_role: Роль текущего пользователя
            
        Returns:
            Список сообщений, связанных с заказом
            
        Raises:
            NotFoundError: Если заказ не найден
            AuthorizationError: Если у пользователя нет доступа к заказу
        """
        # Загрузить order с items заранее, чтобы избежать lazy loading проблем
        result = await self.db.execute(
            select(Order).options(selectinload(Order.items).selectinload(OrderItem.item)).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            raise NotFoundError("Order", order_id)
        
        # Проверить доступ: пользователь должен быть владельцем заказа, продавцом, админом или поддержкой
        has_access = (
            order.user_id == user_id or
            user_role == UserRole.ADMIN or
            user_role == UserRole.SUPPORT or
            (user_role == UserRole.SELLER and order.items and any(
                item.item.owner_id == user_id for item in order.items
            ))
        )
        
        if not has_access:
            raise AuthorizationError("У вас нет прав для просмотра этого чата")
        
        # Получить сообщения
        result = await self.db.execute(
            select(Message)
            .options(
                selectinload(Message.sender),
                selectinload(Message.receiver),
                selectinload(Message.order)
            )
            .where(Message.order_id == order_id)
            .order_by(Message.created_at.asc())
        )
        return list(result.scalars().all())
    
    async def get_support_conversations(
        self,
        support_user_id: int,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[dict], int]:
        """
        Получить всех пользователей, у которых есть беседы с поддержкой.
        
        Args:
            support_user_id: ID пользователя поддержки
            skip: Количество бесед для пропуска
            limit: Максимальное количество бесед для возврата
            
        Returns:
            Кортеж (список бесед, общее количество)
        """
        # Получить всех пользователей, которые отправляли или получали сообщения с поддержкой
        # Получить уникальные ID пользователей, у которых есть беседы с поддержкой
        sent_result = await self.db.execute(
            select(
                Message.sender_id.label("user_id"),
                func.max(Message.created_at).label("last_message_at")
            )
            .where(
                and_(
                    Message.receiver_id == support_user_id,
                    Message.is_resolved == False
                )
            )
            .group_by(Message.sender_id)
        )
        sent_users = {row.user_id: row.last_message_at for row in sent_result.all()}
        
        received_result = await self.db.execute(
            select(
                Message.receiver_id.label("user_id"),
                func.max(Message.created_at).label("last_message_at")
            )
            .where(
                and_(
                    Message.sender_id == support_user_id,
                    Message.is_resolved == False
                )
            )
            .group_by(Message.receiver_id)
        )
        received_users = {row.user_id: row.last_message_at for row in received_result.all()}
        
        # Объединить и получить время последнего сообщения для каждого пользователя
        all_users = set(sent_users.keys()) | set(received_users.keys())
        user_times = {}
        for user_id in all_users:
            sent_time = sent_users.get(user_id)
            received_time = received_users.get(user_id)
            if sent_time and received_time:
                user_times[user_id] = max(sent_time, received_time)
            elif sent_time:
                user_times[user_id] = sent_time
            else:
                user_times[user_id] = received_time
        
        # Сортировать по времени последнего сообщения (новые первыми)
        sorted_users = sorted(user_times.items(), key=lambda x: x[1], reverse=True)
        total = len(sorted_users)
        
        # Применить пагинацию
        paginated_users = sorted_users[skip:skip + limit]
        
        # Получить детали пользователя и последнее сообщение для каждой беседы
        conversations = []
        for user_id, _ in paginated_users:
            # Получить пользователя
            user_result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one()
            
            # Получить последнее сообщение (только нерешенные)
            last_message_result = await self.db.execute(
                select(Message)
                .options(selectinload(Message.sender), selectinload(Message.receiver))
                .where(
                    and_(
                        or_(
                            and_(Message.sender_id == user_id, Message.receiver_id == support_user_id),
                            and_(Message.sender_id == support_user_id, Message.receiver_id == user_id)
                        ),
                        Message.is_resolved == False
                    )
                )
                .order_by(Message.created_at.desc())
                .limit(1)
            )
            last_message = last_message_result.scalar_one_or_none()
            
            # Получить количество непрочитанных (сообщения от пользователя к поддержке, которые не прочитаны)
            unread_result = await self.db.execute(
                select(func.count(Message.id)).where(
                    and_(
                        Message.sender_id == user_id,
                        Message.receiver_id == support_user_id,
                        Message.is_read == False
                    )
                )
            )
            unread_count = unread_result.scalar() or 0
            
            conversations.append({
                "user": user,
                "last_message": last_message,
                "unread_count": unread_count
            })
        
        return conversations, total
    
    async def resolve_conversation(
        self,
        user1_id: int,
        user2_id: int,
        resolved_by_id: int
    ) -> int:
        """
        Mark all messages in a conversation between two users as resolved.
        
        Args:
            user1_id: First user ID
            user2_id: Second user ID
            resolved_by_id: ID of user who resolved the conversation
            
        Returns:
            Number of messages marked as resolved
        """
        from sqlalchemy import update
        
        stmt = (
            update(Message)
            .where(
                or_(
                    and_(Message.sender_id == user1_id, Message.receiver_id == user2_id),
                    and_(Message.sender_id == user2_id, Message.receiver_id == user1_id)
                ),
                Message.is_resolved == False
            )
            .values(is_resolved=True)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount
    
    async def delete_conversation(
        self,
        user1_id: int,
        user2_id: int,
        deleted_by_id: int
    ) -> int:
        """
        Delete all messages in a conversation between two users.
        
        Args:
            user1_id: First user ID
            user2_id: Second user ID
            deleted_by_id: ID of user who deleted the conversation
            
        Returns:
            Number of messages deleted
        """
        from sqlalchemy import delete
        
        stmt = (
            delete(Message)
            .where(
                or_(
                    and_(Message.sender_id == user1_id, Message.receiver_id == user2_id),
                    and_(Message.sender_id == user2_id, Message.receiver_id == user1_id)
                )
            )
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount
