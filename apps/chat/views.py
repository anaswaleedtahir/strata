from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import Http404
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.views import View

from apps.chat.selectors import (
    conversation_get_for_user,
    conversation_list_for_user,
    messages_for_conversation,
)
from apps.chat.services import conversation_start, messages_mark_read
from apps.properties.selectors import property_get_with_related
from apps.shared.exceptions import ApplicationError


class ConversationListView(LoginRequiredMixin, View):
    def get(self, request):
        conversations = conversation_list_for_user(user=request.user)
        return render(
            request, "chat/conversation_list.html", {"conversations": conversations}
        )


class ConversationDetailView(LoginRequiredMixin, View):
    def get(self, request, conversation_id):
        try:
            conversation, other_participant = conversation_get_for_user(
                conversation_id=conversation_id, user=request.user
            )
        except ApplicationError as e:
            return HttpResponseForbidden(e.message)

        page_obj = Paginator(
            messages_for_conversation(conversation=conversation), 50
        ).get_page(request.GET.get("page", 1))
        is_live_page = page_obj.number == 1
        chat_messages = list(reversed(page_obj.object_list))
        for message in chat_messages:
            message.was_unread = (
                is_live_page and not message.is_read and message.sender != request.user
            )
        if is_live_page:
            messages_mark_read(conversation=conversation, user=request.user)

        context = {
            "conversation": conversation,
            "chat_messages": chat_messages,
            "other_participant": other_participant,
            "page_obj": page_obj,
            "is_live_page": is_live_page,
        }
        return render(request, "chat/conversation_detail.html", context)


class StartConversationView(LoginRequiredMixin, View):
    def post(self, request, property_id):
        property_obj = property_get_with_related(pk=property_id)
        if property_obj is None or not property_obj.is_published:
            raise Http404("Property not found")

        try:
            conversation = conversation_start(
                user=request.user, property_obj=property_obj
            )
        except ApplicationError as e:
            return HttpResponseForbidden(e.message)

        return redirect("chat:conversation_detail", conversation_id=conversation.id)
