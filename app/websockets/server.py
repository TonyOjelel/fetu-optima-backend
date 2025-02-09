from fastapi import WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Set, Optional
import json
from app.core.security import get_current_user
from app.core.cache import get_redis, CacheService

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        self.user_channels: Dict[int, Set[str]] = {}

    async def connect(self, websocket: WebSocket, user_id: int, channel: Optional[str] = None):
        await websocket.accept()
        
        # Initialize user connections if not exists
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
            self.user_channels[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        if channel:
            self.user_channels[user_id].add(channel)

    async def disconnect(self, websocket: WebSocket, user_id: int):
        self.active_connections[user_id].remove(websocket)
        if not self.active_connections[user_id]:
            del self.active_connections[user_id]
            del self.user_channels[user_id]

    async def send_personal_message(self, message: dict, user_id: int):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await connection.send_json(message)

    async def broadcast(self, message: dict, channel: Optional[str] = None):
        for user_id, channels in self.user_channels.items():
            if not channel or channel in channels:
                await self.send_personal_message(message, user_id)

manager = ConnectionManager()

async def get_token(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing authentication token")
        return None
    return token

async def websocket_endpoint(
    websocket: WebSocket,
    channel: Optional[str] = None,
    redis: Redis = Depends(get_redis)
):
    token = await get_token(websocket)
    if not token:
        return

    try:
        user = await get_current_user(token)
    except:
        await websocket.close(code=4002, reason="Invalid authentication token")
        return

    await manager.connect(websocket, user.id, channel)
    cache = CacheService(redis)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                
                # Handle different message types
                if message["type"] == "leaderboard_subscribe":
                    # Subscribe to leaderboard updates
                    self.user_channels[user.id].add("leaderboard")
                    
                    # Send initial leaderboard data
                    leaderboard = await cache.get_sorted_set_range("leaderboard", 0, 9, desc=True)
                    await manager.send_personal_message({
                        "type": "leaderboard_update",
                        "data": leaderboard
                    }, user.id)
                
                elif message["type"] == "puzzle_progress":
                    # Broadcast puzzle progress to other users
                    await manager.broadcast({
                        "type": "user_progress",
                        "data": {
                            "user_id": user.id,
                            "puzzle_id": message["puzzle_id"],
                            "progress": message["progress"]
                        }
                    }, f"puzzle_{message['puzzle_id']}")

            except json.JSONDecodeError:
                await manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid message format"
                }, user.id)

    except WebSocketDisconnect:
        await manager.disconnect(websocket, user.id)

async def send_leaderboard_update(redis: Redis):
    """Send leaderboard updates to subscribed users"""
    cache = CacheService(redis)
    leaderboard = await cache.get_sorted_set_range("leaderboard", 0, 9, desc=True)
    
    await manager.broadcast({
        "type": "leaderboard_update",
        "data": leaderboard
    }, channel="leaderboard")

async def send_puzzle_notification(user_id: int, puzzle_id: int, notification_type: str):
    """Send puzzle-related notifications to users"""
    await manager.send_personal_message({
        "type": "puzzle_notification",
        "data": {
            "puzzle_id": puzzle_id,
            "notification_type": notification_type
        }
    }, user_id)
