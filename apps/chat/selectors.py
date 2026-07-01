from django.db.models import Count, OuterRef, Prefetch, Q, QuerySet, Subquery
from django.shortcuts import get_object_or_404

from apps.chat.models import Conversation
from apps.properties.models import PropertyImage
from apps.shared.exceptions import ApplicationError


def conversation_list_for_user(*, user) -> list[Conversation]:
    latest_message = Conversation.messages.rel.related_model.objects.filter(
        conversation_id=OuterRef("pk")
    ).order_by("-created_at", "-id")
    conversations = list(
        Conversation.objects.filter(Q(participant_one=user) | Q(participant_two=user))
        .select_related("property", "participant_one", "participant_two")
        .prefetch_related(
            Prefetch(
                "property__images",
                queryset=PropertyImage.objects.order_by("created_at"),
                to_attr="prefetched_images",
            )
        )
        .annotate(
            unread_count=Count(
                "messages",
                filter=Q(messages__is_read=False) & ~Q(messages__sender=user),
            ),
            latest_message_id=Subquery(latest_message.values("id")[:1]),
            latest_message_content=Subquery(latest_message.values("content")[:1]),
            latest_message_sender_id=Subquery(latest_message.values("sender_id")[:1]),
        )
        .order_by("-updated_at")
    )
    for conversation in conversations:
        conversation.other_participant = (
            conversation.participant_two
            if conversation.participant_one == user
            else conversation.participant_one
        )
        conversation.primary_image = next(
            iter(getattr(conversation.property, "prefetched_images", [])), None
        )
    return conversations


def conversation_get_for_user(
    *, conversation_id: int, user
) -> tuple[Conversation, object]:
    conversation = get_object_or_404(
        Conversation.objects.select_related(
            "participant_one", "participant_two", "property"
        ),
        id=conversation_id,
    )
    if conversation.participant_one != user and conversation.participant_two != user:
        raise ApplicationError("You are not a participant in this conversation.")
    other_participant = (
        conversation.participant_two
        if conversation.participant_one == user
        else conversation.participant_one
    )
    return conversation, other_participant


def conversation_get(*, conversation_id: int) -> Conversation | None:
    return (
        Conversation.objects.filter(id=conversation_id)
        .select_related("participant_one", "participant_two", "property")
        .first()
    )


def messages_for_conversation(*, conversation: Conversation) -> QuerySet:
    return conversation.messages.select_related("sender").order_by("-created_at", "-id")
