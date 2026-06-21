import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings

from apps.chat.selectors import conversation_get
from apps.chat.services import message_deliver
from apps.shared.exceptions import ApplicationError

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.room_group_name = f"chat_{self.conversation_id}"
        self.user = self.scope.get("user")

        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return

        self.conversation = await database_sync_to_async(conversation_get)(
            conversation_id=self.conversation_id
        )

        if not self.conversation:
            await self.close(code=4004)
            return

        is_participant = (
            self.conversation.participant_one_id == self.user.id
            or self.conversation.participant_two_id == self.user.id
        )
        if not is_participant:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            msg_type = data.get("type", "chat_message")
            await self._dispatch(msg_type, data)
        except json.JSONDecodeError:
            await self._send_error("Invalid message format")
        except Exception as exc:
            logger.exception("Unexpected error in receive(): %s", exc)
            await self._send_error("An error occurred while processing your message")

    async def _dispatch(self, msg_type: str, data: dict):
        if msg_type == "ping":
            await self.send(text_data=json.dumps({"type": "pong"}))
            return

        if msg_type != "chat_message":
            await self._send_error("Unknown message type")
            return

        try:
            message = await message_deliver(
                conversation=self.conversation,
                sender=self.user,
                content=data.get("message", ""),
                redis_url=settings.REDIS_URL,
            )
        except ApplicationError as error:
            cooldown_seconds = error.extra.get("cooldown_seconds")
            if cooldown_seconds is None:
                await self._send_error(error.message)
            else:
                await self.send(
                    text_data=json.dumps(
                        {
                            "type": "rate_limit_error",
                            "message": error.message,
                            "cooldown_seconds": cooldown_seconds,
                            "status_code": 429,
                        }
                    )
                )
            return
        except Exception as exc:
            logger.exception(
                "Failed to deliver message for conversation %s: %s",
                self.conversation_id,
                exc,
            )
            await self._send_error("Failed to save message")
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message.content,
                "sender_id": self.user.id,
                "sender_email": self.user.email,
                "message_id": message.id,
                "created_at": message.created_at.isoformat(),
            },
        )

    async def _send_error(self, message: str):
        await self.send(text_data=json.dumps({"type": "error", "message": message}))

    async def chat_message(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "message",
                    "message": event["message"],
                    "sender_id": event["sender_id"],
                    "sender_email": event["sender_email"],
                    "message_id": event["message_id"],
                    "created_at": event["created_at"],
                }
            )
        )
