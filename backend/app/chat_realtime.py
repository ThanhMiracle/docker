"""In-process WebSocket fan-out for support chat notifications."""

from collections import defaultdict
from fastapi import WebSocket


class ChatConnectionManager:
    def __init__(self):
        self.connections: dict[int, set[WebSocket]] = defaultdict(set)

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.connections[user_id].add(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket):
        self.connections[user_id].discard(websocket)
        if not self.connections[user_id]:
            self.connections.pop(user_id, None)

    async def notify(self, user_ids: list[int], event: dict):
        for user_id in set(user_ids):
            for websocket in list(self.connections.get(user_id, set())):
                try:
                    await websocket.send_json(event)
                except Exception:
                    self.disconnect(user_id, websocket)


chat_connections = ChatConnectionManager()
