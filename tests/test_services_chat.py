"""Tests for ChatService."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from app.services.chat_service import ChatService
from app.models import Message, User, Order, OrderStatus, UserRole
from app.core.exceptions import NotFoundError, AuthorizationError


@pytest.mark.asyncio
async def test_send_message_receiver_not_found(db_session: AsyncSession, test_user):
    """Test sending message to non-existent receiver."""
    service = ChatService(db_session)
    with pytest.raises(NotFoundError):
        await service.send_message(test_user.id, 999, "Test message")


@pytest.mark.asyncio
async def test_send_message_with_order_not_found(db_session: AsyncSession, test_user, test_seller):
    """Test sending message with non-existent order."""
    service = ChatService(db_session)
    with pytest.raises(NotFoundError):
        await service.send_message(test_user.id, test_seller.id, "Test", order_id=999)


@pytest.mark.asyncio
async def test_send_message_with_order(db_session: AsyncSession, test_user, test_seller, test_item):
    """Test sending message with order."""
    order = Order(
        user_id=test_user.id,
        total_price=1000.0,
        status=OrderStatus.PENDING,
        shipping_address="Test"
    )
    db_session.add(order)
    await db_session.flush()
    
    service = ChatService(db_session)
    message = await service.send_message(test_user.id, test_seller.id, "Test message", order_id=order.id)
    assert message.text == "Test message"
    assert message.order_id == order.id


@pytest.mark.asyncio
async def test_get_conversation_empty(db_session: AsyncSession, test_user, test_seller):
    """Test getting empty conversation."""
    service = ChatService(db_session)
    messages, total = await service.get_conversation(test_user.id, test_seller.id)
    assert messages == []
    assert total == 0


@pytest.mark.asyncio
async def test_get_conversation_with_order(db_session: AsyncSession, test_user, test_seller):
    """Test getting conversation filtered by order."""
    order = Order(
        user_id=test_user.id,
        total_price=1000.0,
        status=OrderStatus.PENDING,
        shipping_address="Test"
    )
    db_session.add(order)
    await db_session.flush()
    
    service = ChatService(db_session)
    message1 = await service.send_message(test_user.id, test_seller.id, "Message 1", order_id=order.id)
    message2 = await service.send_message(test_user.id, test_seller.id, "Message 2")
    
    messages, total = await service.get_conversation(test_user.id, test_seller.id, order_id=order.id)
    assert total == 1
    assert messages[0].id == message1.id


@pytest.mark.asyncio
async def test_get_user_conversations_empty(db_session: AsyncSession, test_user):
    """Test getting user conversations when empty."""
    service = ChatService(db_session)
    conversations, total = await service.get_user_conversations(test_user.id)
    assert conversations == []
    assert total == 0


@pytest.mark.asyncio
async def test_get_user_conversations(db_session: AsyncSession, test_user, test_seller):
    """Test getting user conversations."""
    service = ChatService(db_session)
    await service.send_message(test_user.id, test_seller.id, "Test message")
    
    conversations, total = await service.get_user_conversations(test_user.id)
    assert total >= 1
    assert any(conv["partner"].id == test_seller.id for conv in conversations)


@pytest.mark.asyncio
async def test_mark_as_read(db_session: AsyncSession, test_user, test_seller):
    """Test marking messages as read."""
    service = ChatService(db_session)
    message1 = await service.send_message(test_seller.id, test_user.id, "Message 1")
    message2 = await service.send_message(test_seller.id, test_user.id, "Message 2")
    
    count = await service.mark_as_read([message1.id, message2.id], test_user.id)
    assert count == 2
    
    # Verify messages are marked as read
    result = await db_session.execute(
        select(Message).where(Message.id.in_([message1.id, message2.id]))
    )
    messages = result.scalars().all()
    assert all(msg.is_read for msg in messages)


@pytest.mark.asyncio
async def test_get_order_chat_not_found(db_session: AsyncSession, test_user):
    """Test getting order chat for non-existent order."""
    service = ChatService(db_session)
    with pytest.raises(NotFoundError):
        await service.get_order_chat(999, test_user.id, test_user.role)


@pytest.mark.asyncio
async def test_get_order_chat_unauthorized(db_session: AsyncSession, test_user, test_seller):
    """Test getting order chat by non-owner."""
    from sqlalchemy.orm import selectinload
    
    order = Order(
        user_id=test_user.id,
        total_price=1000.0,
        status=OrderStatus.PENDING,
        shipping_address="Test"
    )
    db_session.add(order)
    await db_session.flush()
    
    # Загрузить order с items заранее, чтобы избежать lazy loading
    from sqlalchemy import select
    result = await db_session.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order.id)
    )
    order = result.scalar_one()
    
    service = ChatService(db_session)
    with pytest.raises(AuthorizationError):
        await service.get_order_chat(order.id, test_seller.id, test_seller.role)


@pytest.mark.asyncio
async def test_get_order_chat_by_admin(db_session: AsyncSession, test_user, test_admin):
    """Test getting order chat by admin."""
    order = Order(
        user_id=test_user.id,
        total_price=1000.0,
        status=OrderStatus.PENDING,
        shipping_address="Test"
    )
    db_session.add(order)
    await db_session.flush()
    
    service = ChatService(db_session)
    await service.send_message(test_user.id, test_admin.id, "Test", order_id=order.id)
    
    messages = await service.get_order_chat(order.id, test_admin.id, UserRole.ADMIN)
    assert len(messages) >= 1


@pytest.mark.asyncio
async def test_get_support_conversations(db_session: AsyncSession, test_user, test_support):
    """Test getting support conversations."""
    service = ChatService(db_session)
    await service.send_message(test_user.id, test_support.id, "Support message")
    
    conversations, total = await service.get_support_conversations(test_support.id)
    assert total >= 1
    assert any(conv["user"].id == test_user.id for conv in conversations)


@pytest.mark.asyncio
async def test_resolve_conversation(db_session: AsyncSession, test_user, test_seller):
    """Test resolving conversation."""
    service = ChatService(db_session)
    message1 = await service.send_message(test_user.id, test_seller.id, "Message 1")
    message2 = await service.send_message(test_seller.id, test_user.id, "Message 2")
    
    count = await service.resolve_conversation(test_user.id, test_seller.id, test_seller.id)
    assert count >= 2
    
    # Verify messages are marked as resolved
    result = await db_session.execute(
        select(Message).where(
            or_(
                and_(Message.sender_id == test_user.id, Message.receiver_id == test_seller.id),
                and_(Message.sender_id == test_seller.id, Message.receiver_id == test_user.id)
            )
        )
    )
    messages = result.scalars().all()
    assert all(msg.is_resolved for msg in messages if msg.id in [message1.id, message2.id])


@pytest.mark.asyncio
async def test_delete_conversation(db_session: AsyncSession, test_user, test_seller):
    """Test deleting conversation."""
    service = ChatService(db_session)
    message1 = await service.send_message(test_user.id, test_seller.id, "Message 1")
    message2 = await service.send_message(test_seller.id, test_user.id, "Message 2")
    
    count = await service.delete_conversation(test_user.id, test_seller.id, test_user.id)
    assert count >= 2
    
    # Verify messages are deleted
    messages, total = await service.get_conversation(test_user.id, test_seller.id)
    assert total == 0

