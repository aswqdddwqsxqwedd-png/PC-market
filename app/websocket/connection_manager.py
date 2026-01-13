"""WebSocket connection manager for chat."""
from typing import Dict, List, Set
from fastapi import WebSocket
import json
import structlog

logger = structlog.get_logger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for chat.
    
    Tracks active connections and routes messages to appropriate users.
    """
    
    def __init__(self):
        """Initialize connection manager."""
        # Map of user_id -> set of WebSocket connections
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # Map of websocket -> user_id for quick lookup
        self.connection_users: Dict[WebSocket, int] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """
        Connect a user's WebSocket.
        
        Args:
            websocket: WebSocket connection
            user_id: User ID
        """
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        self.connection_users[websocket] = user_id
        
        logger.info("websocket_connected", user_id=user_id, total_connections=len(self.active_connections[user_id]))
    
    def disconnect(self, websocket: WebSocket):
        """
        Disconnect a WebSocket.
        
        Args:
            websocket: WebSocket connection to disconnect
        """
        user_id = self.connection_users.get(websocket)
        if user_id:
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            del self.connection_users[websocket]
            
            logger.info("websocket_disconnected", user_id=user_id)
    
    async def send_personal_message(self, message: dict, user_id: int):
        """
        Send a message to a specific user.
        
        Args:
            message: Message dictionary to send
            user_id: Target user ID
        """
        if user_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error("websocket_send_error", user_id=user_id, error=str(e))
                    disconnected.add(connection)
            
            # Clean up disconnected connections
            for conn in disconnected:
                self.disconnect(conn)
    
    async def broadcast_to_order_participants(
        self,
        message: dict,
        order_id: int,
        sender_id: int,
        participant_ids: List[int]
    ):
        """
        Broadcast message to all participants of an order chat.
        
        Args:
            message: Message dictionary to send
            order_id: Order ID
            sender_id: ID of message sender (won't receive the message)
            participant_ids: List of participant user IDs
        """
        sent_to = set()
        for user_id in participant_ids:
            if user_id != sender_id:  # Don't send to sender
                await self.send_personal_message(message, user_id)
                sent_to.add(user_id)
        
        logger.info(
            "message_broadcast",
            order_id=order_id,
            sender_id=sender_id,
            recipients=list(sent_to)
        )
    
    def is_connected(self, user_id: int) -> bool:
        """
        Check if user has active WebSocket connection.
        
        Args:
            user_id: User ID to check
            
        Returns:
            True if user has active connection
        """
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0
    
    def get_connected_users(self) -> List[int]:
        """
        Get list of currently connected user IDs.
        
        Returns:
            List of user IDs with active connections
        """
        return list(self.active_connections.keys())


# Global connection manager instance
manager = ConnectionManager()

