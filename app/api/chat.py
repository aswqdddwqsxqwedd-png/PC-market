"""API-роуты для чата и сообщений."""
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.db import get_db
from app.api.deps import get_current_user, get_current_user_optional
from app.models import User, UserRole, Order
from app.services import ChatService
from app.websocket.connection_manager import manager
from app.schemas.chat import (
    MessageCreate, MessageResponse, ConversationListResponse,
    MessageListResponse, ConversationResponse
)
from app.core.exceptions import NotFoundError, AuthorizationError
import json
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    """
    WebSocket-эндпоинт для чата в реальном времени.
    
    Args:
        websocket: WebSocket-соединение
        user_id: ID аутентифицированного пользователя (должен проверяться по токену в продакшене)
    """
    await manager.connect(websocket, user_id)
    
    try:
        while True:
            # Получить сообщение от клиента
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Обработать различные типы сообщений
            message_type = message_data.get("type")
            
            if message_type == "ping":
                # Проверка связи
                await websocket.send_json({"type": "pong"})
            elif message_type == "message":
                # Обработать отправку сообщения через WebSocket
                # В продакшене это должно обрабатываться через HTTP POST для лучшей валидации
                logger.info("websocket_message_received", user_id=user_id, data=message_data)
                await websocket.send_json({
                    "type": "error",
                    "message": "Используйте HTTP POST /api/v1/chat/messages для отправки сообщений"
                })
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("websocket_disconnected", user_id=user_id)


@router.post("/messages", response_model=MessageResponse, status_code=201)
async def send_message(
    message_data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Отправить сообщение.
    
    Args:
        message_data: Данные для создания сообщения
        db: Сессия базы данных
        current_user: Текущий аутентифицированный пользователь
        
    Returns:
        Созданное сообщение
    """
    service = ChatService(db)
    sender_id = current_user.id
    # Если сообщение отправляет админ пользователю, то оно должно отправляться от имени поддержки
    if current_user.role == UserRole.ADMIN:
        # Проверяем, что получатель - обычный пользователь
        receiver_user = await db.get(User, message_data.receiver_id)
        if receiver_user and receiver_user.role == UserRole.USER:
            from sqlalchemy import select
            support_result = await db.execute(
                select(User).where(User.role == UserRole.SUPPORT, User.is_active == True).limit(1)
            )
            support_user = support_result.scalar_one_or_none()
            if support_user:
                sender_id = support_user.id

    message = await service.send_message(
        sender_id=sender_id,
        receiver_id=message_data.receiver_id,
        text=message_data.text,
        order_id=message_data.order_id,
        item_id=message_data.item_id
    )
    
    # Отправить через WebSocket, если получатель подключен
    message_dict = {
        "type": "new_message",
        "message": {
            "id": message.id,
            "sender_id": message.sender_id,
            "receiver_id": message.receiver_id,
            "text": message.text,
            "order_id": message.order_id,
            "created_at": message.created_at.isoformat(),
            "sender_username": message.sender.username
        }
    }
    await manager.send_personal_message(message_dict, message.receiver_id)
    
    return MessageResponse(
        id=message.id,
        sender_id=message.sender_id,
        receiver_id=message.receiver_id,
        order_id=message.order_id,
        item_id=message.item_id,
        text=message.text,
        is_read=message.is_read,
        created_at=message.created_at,
        sender_username=message.sender.username,
        receiver_username=message.receiver.username,
        sender_role=message.sender.role.value if message.sender.role else None,
        receiver_role=message.receiver.role.value if message.receiver.role else None
    )


@router.get("/conversations", response_model=ConversationListResponse)
async def get_conversations(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить все беседы текущего пользователя.
    
    Args:
        page: Номер страницы
        limit: Элементов на странице
        db: Сессия базы данных
        current_user: Текущий аутентифицированный пользователь
        
    Returns:
        Список бесед
    """
    service = ChatService(db)
    skip = (page - 1) * limit
    conversations, total = await service.get_user_conversations(
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )
    
    pages = (total + limit - 1) // limit
    
    # Преобразовать в формат ответа
    conversation_responses = []
    for conv in conversations:
        last_msg = None
        if conv["last_message"]:
            msg = conv["last_message"]
            last_msg = MessageResponse(
                id=msg.id,
                sender_id=msg.sender_id,
                receiver_id=msg.receiver_id,
                order_id=msg.order_id,
                item_id=msg.item_id,
                text=msg.text,
                is_read=msg.is_read,
                created_at=msg.created_at,
                sender_username=msg.sender.username,
                receiver_username=msg.receiver.username,
                sender_role=msg.sender.role.value if msg.sender.role else None,
                receiver_role=msg.receiver.role.value if msg.receiver.role else None
            )
        
        conversation_responses.append(ConversationResponse(
            partner_id=conv["partner"].id,
            partner_username=conv["partner"].username,
            partner_role=conv["partner"].role,
            last_message=last_msg,
            unread_count=conv["unread_count"]
        ))
    
    return ConversationListResponse(
        conversations=conversation_responses,
        total=total,
        page=page,
        pages=pages
    )


@router.get("/conversations/{partner_id}/messages", response_model=MessageListResponse)
async def get_conversation_messages(
    partner_id: int,
    order_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get messages in a conversation with a specific user.
    
    Args:
        partner_id: Partner user ID
        order_id: Optional order ID to filter by
        page: Page number
        limit: Items per page
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List of messages
    """
    service = ChatService(db)
    skip = (page - 1) * limit
    # Если админ или поддержка запрашивают сообщения с пользователем,
    # нужно использовать ID поддержки для получения правильных сообщений
    user1_id = current_user.id
    user2_id = partner_id
    
    # Если текущий пользователь - админ или поддержка, и партнер - обычный пользователь,
    # нужно найти ID поддержки для правильной загрузки сообщений
    if current_user.role in [UserRole.ADMIN, UserRole.SUPPORT]:
        # Проверить, есть ли сообщения между текущим пользователем и партнером
        # Если нет, попробовать найти через поддержку
        from sqlalchemy import select
        if current_user.role == UserRole.ADMIN:
            # Для админа: найти ID поддержки
            support_result = await db.execute(
                select(User).where(User.role == UserRole.SUPPORT, User.is_active == True).limit(1)
            )
            support_user = support_result.scalar_one_or_none()
            if support_user:
                # Использовать ID поддержки вместо ID админа
                user1_id = support_user.id
    
    messages, total = await service.get_conversation(
        user1_id=user1_id,
        user2_id=user2_id,
        order_id=order_id,
        skip=skip,
        limit=limit
    )
    
    pages = (total + limit - 1) // limit
    
    message_responses = [
        MessageResponse(
            id=msg.id,
            sender_id=msg.sender_id,
            receiver_id=msg.receiver_id,
            order_id=msg.order_id,
            item_id=msg.item_id,
            text=msg.text,
            is_read=msg.is_read,
            created_at=msg.created_at,
            sender_username=msg.sender.username,
            receiver_username=msg.receiver.username,
            sender_role=msg.sender.role.value if msg.sender.role else None,
            receiver_role=msg.receiver.role.value if msg.receiver.role else None
        )
        for msg in messages
    ]
    
    return MessageListResponse(
        messages=message_responses,
        total=total,
        page=page,
        pages=pages
    )


@router.get("/orders/{order_id}/messages", response_model=MessageListResponse)
async def get_order_messages(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get chat messages for a specific order.
    
    Available to:
    - Order owner (buyer)
    - Seller of items in the order
    - Admin
    - Support
    
    Args:
        order_id: Order ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List of messages related to the order
    """
    service = ChatService(db)
    messages = await service.get_order_chat(
        order_id=order_id,
        user_id=current_user.id,
        user_role=current_user.role
    )
    
    message_responses = [
        MessageResponse(
            id=msg.id,
            sender_id=msg.sender_id,
            receiver_id=msg.receiver_id,
            order_id=msg.order_id,
            item_id=msg.item_id,
            text=msg.text,
            is_read=msg.is_read,
            created_at=msg.created_at,
            sender_username=msg.sender.username,
            receiver_username=msg.receiver.username,
            sender_role=msg.sender.role.value if msg.sender.role else None,
            receiver_role=msg.receiver.role.value if msg.receiver.role else None
        )
        for msg in messages
    ]
    
    return MessageListResponse(
        messages=message_responses,
        total=len(message_responses),
        page=1,
        pages=1
    )


@router.post("/messages/{message_id}/read")
async def mark_message_read(
    message_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Отметить сообщение как прочитанное.
    
    Args:
        message_id: ID сообщения для отметки как прочитанное
        db: Сессия базы данных
        current_user: Текущий аутентифицированный пользователь
        
    Returns:
        Сообщение об успехе
    """
    service = ChatService(db)
    count = await service.mark_as_read([message_id], current_user.id)
    
    if count == 0:
        raise NotFoundError("Message", message_id)
    
    return {"message": "Сообщение отмечено как прочитанное", "count": count}


@router.post("/support/connect")
async def connect_to_support(
    order_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Подключить пользователя к поддержке.
    
    Создает или возвращает существующую беседу с поддержкой.
    
    Args:
        order_id: Опциональный ID заказа, если запрос поддержки связан с заказом
        db: Сессия базы данных
        current_user: Текущий аутентифицированный пользователь
        
    Returns:
        Информация о пользователе поддержки и детали беседы
    """
    from sqlalchemy import select
    
    # Найти пользователя поддержки
    result = await db.execute(
        select(User).where(User.role == UserRole.SUPPORT, User.is_active == True).limit(1)
    )
    support_user = result.scalar_one_or_none()
    
    if not support_user:
        raise NotFoundError("Support", "Нет доступного персонала поддержки")
    
    service = ChatService(db)
    
    # Получить или создать беседу (без автоматического приветственного сообщения)
    messages, _ = await service.get_conversation(
        user1_id=current_user.id,
        user2_id=support_user.id,
        order_id=order_id,
        limit=1
    )
    
    return {
        "support_user_id": support_user.id,
        "support_username": support_user.username,
        "order_id": order_id
    }


@router.get("/support/conversations")
async def get_support_conversations(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить всех пользователей, у которых есть беседы с поддержкой.
    
    Доступно только для персонала поддержки и админов.
    
    Args:
        page: Page number
        limit: Number of conversations per page
        db: Database session
        current_user: Current authenticated user (must be support or admin)
        
    Returns:
        List of conversations with users
    """
    # Проверить, является ли пользователь поддержкой или админом
    if current_user.role not in [UserRole.SUPPORT, UserRole.ADMIN]:
        raise AuthorizationError("Только персонал поддержки и админы могут получить доступ к этому эндпоинту")
    
    # Если пользователь админ, нужно найти пользователя поддержки для получения бесед
    # Если пользователь поддержка, использовать его ID
    if current_user.role == UserRole.SUPPORT:
        support_user_id = current_user.id
    else:
        # Админ: найти первого пользователя поддержки
        from sqlalchemy import select
        result = await db.execute(
            select(User).where(User.role == UserRole.SUPPORT, User.is_active == True).limit(1)
        )
        support_user = result.scalar_one_or_none()
        if not support_user:
            return {"conversations": [], "total": 0, "page": page, "limit": limit}
        support_user_id = support_user.id
    
    service = ChatService(db)
    skip = (page - 1) * limit
    conversations, total = await service.get_support_conversations(
        support_user_id=support_user_id,
        skip=skip,
        limit=limit
    )
    
    # Форматировать ответ
    formatted_conversations = []
    for conv in conversations:
        user = conv["user"]
        last_message = conv["last_message"]
        formatted_conversations.append({
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role.value,
            "last_message": {
                "id": last_message.id,
                "text": last_message.text,
                "sender_id": last_message.sender_id,
                "receiver_id": last_message.receiver_id,
                "created_at": last_message.created_at.isoformat(),
                "is_read": last_message.is_read
            } if last_message else None,
            "unread_count": conv["unread_count"]
        })
    
    return {
        "conversations": formatted_conversations,
        "total": total,
        "page": page,
        "limit": limit
    }


@router.get("/support/status")
async def get_support_status(
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Получить статус поддержки (онлайн/оффлайн).
    
    Args:
        db: Сессия базы данных
        current_user: Текущий пользователь (опционально)
        
    Returns:
        Статус поддержки и список онлайн-операторов
    """
    from sqlalchemy import select
    from app.models import User, UserRole
    
    # Найти всех активных пользователей поддержки
    support_result = await db.execute(
        select(User).where(
            User.role == UserRole.SUPPORT,
            User.is_active == True
        )
    )
    support_users = support_result.scalars().all()
    
    # Проверить, кто из них онлайн
    online_support_ids = []
    for support_user in support_users:
        if manager.is_connected(support_user.id):
            online_support_ids.append(support_user.id)
    
    # Также проверить админов (они тоже могут быть поддержкой)
    admin_result = await db.execute(
        select(User).where(
            User.role == UserRole.ADMIN,
            User.is_active == True
        )
    )
    admin_users = admin_result.scalars().all()
    
    online_admin_ids = []
    for admin_user in admin_users:
        if manager.is_connected(admin_user.id):
            online_admin_ids.append(admin_user.id)
    
    is_online = len(online_support_ids) > 0 or len(online_admin_ids) > 0
    
    return {
        "is_online": is_online,
        "online_support_count": len(online_support_ids),
        "online_admin_count": len(online_admin_ids),
        "total_support_count": len(support_users),
        "total_admin_count": len(admin_users)
    }


@router.post("/conversations/{partner_id}/resolve")
async def resolve_conversation(
    partner_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Отметить беседу как решенную (заархивировать).
    
    Доступно только для персонала поддержки и админов.
    
    Args:
        partner_id: ID пользователя-партнера (пользователь, который общался с поддержкой)
        db: Сессия базы данных
        current_user: Текущий аутентифицированный пользователь (должен быть поддержкой или админом)
        
    Returns:
        Сообщение об успехе с количеством решенных сообщений
    """
    # Проверить, является ли пользователь поддержкой или админом
    if current_user.role not in [UserRole.SUPPORT, UserRole.ADMIN]:
        raise AuthorizationError("Только персонал поддержки и админы могут решать беседы")
    
    # Если админ, найти пользователя поддержки для получения беседы
    if current_user.role == UserRole.ADMIN:
        from sqlalchemy import select
        result = await db.execute(
            select(User).where(User.role == UserRole.SUPPORT, User.is_active == True).limit(1)
        )
        support_user = result.scalar_one_or_none()
        if not support_user:
            raise NotFoundError("Support", "No support staff available")
        user1_id = support_user.id
        user2_id = partner_id
    else:
        user1_id = current_user.id
        user2_id = partner_id
    
    service = ChatService(db)
    count = await service.resolve_conversation(
        user1_id=user1_id,
        user2_id=user2_id,
        resolved_by_id=current_user.id
    )
    
    return {
        "message": "Conversation resolved",
        "resolved_count": count
    }


@router.delete("/conversations/{partner_id}")
async def delete_conversation(
    partner_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Удалить беседу.
    
    Доступно только для персонала поддержки и админов.
    
    Args:
        partner_id: ID пользователя-партнера
        db: Сессия базы данных
        current_user: Текущий аутентифицированный пользователь (должен быть поддержкой или админом)
        
    Returns:
        Сообщение об успехе с количеством удаленных сообщений
    """
    # Проверить, является ли пользователь поддержкой или админом
    if current_user.role not in [UserRole.SUPPORT, UserRole.ADMIN]:
        raise AuthorizationError("Только персонал поддержки и админы могут удалять беседы")
    
    # Если админ, найти пользователя поддержки для получения беседы
    if current_user.role == UserRole.ADMIN:
        from sqlalchemy import select
        result = await db.execute(
            select(User).where(User.role == UserRole.SUPPORT, User.is_active == True).limit(1)
        )
        support_user = result.scalar_one_or_none()
        if not support_user:
            raise NotFoundError("Support", "No support staff available")
        user1_id = support_user.id
        user2_id = partner_id
    else:
        user1_id = current_user.id
        user2_id = partner_id
    
    service = ChatService(db)
    count = await service.delete_conversation(
        user1_id=user1_id,
        user2_id=user2_id,
        deleted_by_id=current_user.id
    )
    
    return {
        "message": "Conversation deleted",
        "deleted_count": count
    }

