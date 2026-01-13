"""Schemas for chat and messaging."""
from pydantic import BaseModel, Field, field_serializer
from typing import Optional
from datetime import datetime
from app.models import UserRole


class MessageCreate(BaseModel):
    """Schema for creating a message."""
    receiver_id: int = Field(..., description="ID of the message receiver")
    text: str = Field(..., min_length=1, max_length=5000, description="Message text")
    order_id: Optional[int] = Field(None, description="Optional order ID if related to an order")
    item_id: Optional[int] = Field(None, description="Optional item ID if related to an item")


class MessageResponse(BaseModel):
    """Schema for message response."""
    id: int
    sender_id: int
    receiver_id: int
    order_id: Optional[int] = None
    item_id: Optional[int] = None
    text: str
    is_read: bool
    created_at: datetime
    
    # Nested user info
    sender_username: str
    receiver_username: str
    sender_role: Optional[str] = None
    receiver_role: Optional[str] = None
    
    @field_serializer('created_at')
    def serialize_datetime(self, dt: datetime) -> str:
        """Сериализуем datetime как ISO с суффиксом Z для UTC."""
        iso_str = dt.isoformat()
        if not iso_str.endswith('Z') and '+' not in iso_str and '-' not in iso_str[10:]:
            return iso_str + 'Z'
        return iso_str
    
    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    """Schema for conversation list response."""
    partner_id: int
    partner_username: str
    partner_role: UserRole
    last_message: Optional[MessageResponse] = None
    unread_count: int = 0


class ConversationListResponse(BaseModel):
    """Schema for list of conversations."""
    conversations: list[ConversationResponse]
    total: int
    page: int
    pages: int


class MessageListResponse(BaseModel):
    """Schema for list of messages."""
    messages: list[MessageResponse]
    total: int
    page: int
    pages: int

