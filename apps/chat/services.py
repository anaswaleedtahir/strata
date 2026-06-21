import time

import nh3
from channels.db import database_sync_to_async

from apps.chat.models import Conversation, Message
from apps.shared.exceptions import ApplicationError

RATE_LIMIT_MESSAGES = 10
RATE_LIMIT_WINDOW = 60


def message_create(*, conversation: Conversation, sender, content: str) -> Message:
    message = Message(conversation=conversation, sender=sender, content=content)
    message.full_clean()
    message.save()
    conversation.save(update_fields=["updated_at"])
    return message


async def message_deliver(
    *, conversation: Conversation, sender, content: str, redis_url: str
) -> Message:
    content = content.strip() if isinstance(content, str) else ""
    if not content:
        raise ApplicationError("Message content cannot be empty")

    if len(content) > 5000:
        raise ApplicationError("Message exceeds maximum length of 5000 characters")

    is_allowed, cooldown_seconds = await rate_limit_check(
        user_id=sender.id, redis_url=redis_url
    )
    if not is_allowed:
        raise ApplicationError(
            (
                "Rate limit exceeded. Please wait "
                f"{cooldown_seconds} seconds before sending another message."
            ),
            extra={"cooldown_seconds": cooldown_seconds},
        )

    recipient_id = (
        conversation.participant_two_id
        if conversation.participant_one_id == sender.id
        else conversation.participant_one_id
    )
    if recipient_id == sender.id:
        raise ApplicationError("Cannot send messages to yourself")

    sanitized_content = nh3.clean(content, tags=set())
    return await database_sync_to_async(message_create)(
        conversation=conversation,
        sender=sender,
        content=sanitized_content,
    )


def conversation_get_or_create(
    *, property_obj, participant_one, participant_two
) -> tuple[Conversation, bool]:
    return Conversation.objects.get_or_create(
        property=property_obj,
        participant_one=participant_one,
        participant_two=participant_two,
    )


def messages_mark_read(*, conversation: Conversation, user) -> None:
    conversation.messages.filter(is_read=False).exclude(sender=user).update(
        is_read=True
    )


async def rate_limit_check(*, user_id: int, redis_url: str) -> tuple[bool, int]:
    from redis.asyncio import Redis as AsyncRedis

    current_time = time.time()
    key = f"rate_limit:chat:{user_id}"
    window_start = current_time - RATE_LIMIT_WINDOW

    async with AsyncRedis.from_url(redis_url, decode_responses=True) as redis:
        async with redis.pipeline(transaction=True) as pipe:
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zadd(key, {str(current_time): current_time})
            pipe.zcard(key)
            pipe.zrange(key, 0, 0, withscores=True)
            pipe.expire(key, RATE_LIMIT_WINDOW)
            _, _, message_count, oldest, _ = await pipe.execute()

    if message_count <= RATE_LIMIT_MESSAGES:
        return True, 0

    cooldown = (
        int(oldest[0][1] + RATE_LIMIT_WINDOW - current_time) + 1
        if oldest
        else RATE_LIMIT_WINDOW
    )
    return False, cooldown


def conversation_start(*, user, property_obj) -> Conversation:
    if not property_obj.is_published:
        raise ApplicationError("Property is not available.")
    if property_obj.user == user:
        raise ApplicationError(
            "You cannot start a conversation with yourself about your own property."
        )
    conversation, _ = conversation_get_or_create(
        property_obj=property_obj,
        participant_one=property_obj.user,
        participant_two=user,
    )
    return conversation
