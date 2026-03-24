from datetime import datetime
from api import FastAPI
from fastapi import WebSocket, WebSocketDisconnect, HTTPException


class WebSocketManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            try:
                await connection.send_json(message)
            except Exception:
                pass


class TicketListener:
    def __init__(self, redis_bus, websocket_manager):
        self.redis = redis_bus
        self.websocket = websocket_manager

    async def process_ticket(self, ticket_data: dict):
        platform = ticket_data.get("platform")
        ticket_id = ticket_data.get("ticket_id")

        self.redis.publish_message(
            f"{platform}:processing",
            {
                "ticket_id": ticket_id,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "received",
            },
        )

        await self.websocket.broadcast(
            {
                "type": "ticket_received",
                "ticket_id": ticket_id,
                "platform": platform,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    async def process_answer(self, ticket_data: dict):
        ticket_id = ticket_data.get("ticket_id")
        answer = ticket_data.get("answer")
        status = ticket_data.get("status")

        self.redis.publish_message(
            "phone:outgoing", {"id": ticket_id, "status": status, "answer": answer}
        )

        await self.websocket.broadcast(
            {
                "type": "ticket_answered",
                "ticket_id": ticket_id,
                "status": status,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )


class WebhookListener:
    def __init__(self, agent: "SupportAgent"):
        self.agent = agent
        self.api = FastAPI()

    @self.api.post("/webhooks/helpscout")
    async def handle_helpscout_webhook(request: dict):
        ticket_data = request.get("data", {})
        ticket_id = ticket_data.get("id")

        if not ticket_id:
            raise HTTPException(status_code=400, detail="Missing ticket ID")

        self.agent.process_ticket(ticket_data)

        return {"status": "received", "ticket_id": ticket_id}

    @self.api.post("/webhooks/facebook")
    async def handle_facebook_webhook(request: dict):
        ticket_data = request.get("data", {})
        ticket_id = ticket_data.get("id")

        if not ticket_id:
            raise HTTPException(status_code=400, detail="Missing comment ID")

        self.agent.process_ticket(ticket_data)

        return {"status": "received", "comment_id": ticket_id}


class PhoneListener:
    def __init__(self, agent: "SupportAgent"):
        self.agent = agent
        self.api = FastAPI()
        self.websocket_manager = WebSocketManager()

    @self.api.websocket("/ws/tickets")
    async def websocket_tickets(websocket: WebSocket):
        client_id = websocket.query_params.get("client_id", "anonymous")
        await self.websocket_manager.connect(websocket, client_id)

        try:
            while True:
                data = await websocket.receive_json()
                message_type = data.get("type")

                if message_type == "subscribe":
                    client_id = data.get("client_id")
                    await self.websocket_manager.connect(websocket, client_id)

                elif message_type == "unsubscribe":
                    await self.websocket_manager.disconnect(client_id)

        except WebSocketDisconnect:
            await self.websocket_manager.disconnect(client_id)
        except Exception:
            await self.websocket_manager.disconnect(client_id)


class PhoneApi:
    def __init__(self, agent: "SupportAgent"):
        self.agent = agent
        self.api = FastAPI()

    @self.api.get("/incoming")
    async def get_incoming_tickets():
        tickets = self.agent.get_pending_tickets()
        return {"tickets": tickets}

    @self.api.get("/answers/{ticket_id}")
    async def get_ticket_answer(ticket_id: str):
        answer = self.agent.get_ticket_answer(ticket_id)
        if not answer:
            raise HTTPException(status_code=404, detail="No answer found")
        return {"answer": answer}
