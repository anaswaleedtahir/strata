from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.urls import reverse
from django.utils.html import format_html

from apps.chat.models import Conversation, Message
from apps.properties.models import Property

User = get_user_model()


class UserFilter(admin.SimpleListFilter):
    title = "user"
    parameter_name = "user"

    def lookups(self, request, model_admin):
        users = User.objects.filter(
            Q(conversations_as_p1__isnull=False) | Q(conversations_as_p2__isnull=False)
        ).distinct()
        return [(user.pk, user.email) for user in users.order_by("email")]

    def queryset(self, request, queryset):
        if not self.value():
            return queryset
        return queryset.filter(
            Q(participant_one_id=self.value()) | Q(participant_two_id=self.value())
        )


class PropertyFilter(admin.SimpleListFilter):
    title = "property"
    parameter_name = "property"

    def lookups(self, request, model_admin):
        properties = (
            Property.objects.filter(conversations__isnull=False)
            .annotate(conversation_count=Count("conversations"))
            .order_by("-created_at")
        )
        return [
            (prop.pk, f"{prop.name} ({prop.conversation_count})") for prop in properties
        ]

    def queryset(self, request, queryset):
        return queryset.filter(property_id=self.value()) if self.value() else queryset


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    can_delete = False
    fields = ("sender", "content_preview", "created_at", "is_read")
    readonly_fields = fields
    ordering = ("created_at",)
    show_change_link = True

    @admin.display(description="Message")
    def content_preview(self, obj):
        return f"{obj.content[:100]}{'…' if len(obj.content) > 100 else ''}"

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "property_link",
        "participant_one_link",
        "participant_two_link",
        "message_count",
        "created_at",
        "updated_at",
    )
    list_filter = (UserFilter, PropertyFilter, "created_at", "updated_at")
    search_fields = (
        "participant_one__email",
        "participant_two__email",
        "property__name",
    )
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"
    inlines = (MessageInline,)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("property", "participant_one", "participant_two")
            .annotate(msg_count=Count("messages"))
        )

    @admin.display(description="Messages", ordering="msg_count")
    def message_count(self, obj):
        return obj.msg_count

    @admin.display(description="Property")
    def property_link(self, obj):
        url = reverse("admin:properties_property_change", args=[obj.property_id])
        return format_html('<a href="{}">{}</a>', url, obj.property.name)

    def _participant_link(self, participant):
        url = reverse("admin:users_user_change", args=[participant.pk])
        return format_html('<a href="{}">{}</a>', url, participant.email)

    @admin.display(description="Participant 1")
    def participant_one_link(self, obj):
        return self._participant_link(obj.participant_one)

    @admin.display(description="Participant 2")
    def participant_two_link(self, obj):
        return self._participant_link(obj.participant_two)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "conversation_link",
        "sender_link",
        "content_preview",
        "created_at",
        "is_read",
    )
    list_filter = ("is_read", "created_at")
    search_fields = (
        "sender__email",
        "content",
        "conversation__participant_one__email",
        "conversation__participant_two__email",
    )
    readonly_fields = ("created_at", "conversation", "sender")
    date_hierarchy = "created_at"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("conversation", "sender")

    @admin.display(description="Content")
    def content_preview(self, obj):
        return f"{obj.content[:50]}{'…' if len(obj.content) > 50 else ''}"

    @admin.display(description="Conversation")
    def conversation_link(self, obj):
        url = reverse("admin:chat_conversation_change", args=[obj.conversation_id])
        return format_html('<a href="{}">Conversation {}</a>', url, obj.conversation_id)

    @admin.display(description="Sender")
    def sender_link(self, obj):
        url = reverse("admin:users_user_change", args=[obj.sender_id])
        return format_html('<a href="{}">{}</a>', url, obj.sender.email)
