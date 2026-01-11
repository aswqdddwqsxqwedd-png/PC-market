from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class MessageCreate(BaseModel):
    receiver_id: int
    item_id: Optional[int] = None
    text: str = Field(..., min_length=1, max_length=2000)


class MessageResponse(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    item_id: Optional[int]
    text: str
    is_read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class ChatMessage(BaseModel):
    """WebSocket message format."""
    type: str  # "message", "typing", "read"
    text: Optional[str] = None
    receiver_id: Optional[int] = None
    item_id: Optional[int] = None
