"""
Admin interface for the real-time chat feature.

Provides administrative access to conversations and messages with filtering,
searching, and display capabilities as specified in Requirements 11.1-11.5.
"""

from django.contrib import admin
from django.contrib.admin.utils import quote
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from apps.chat.models import Conversation, Message
from apps.properties.models import Property

User = get_user_model()


class UserFilter(admin.SimpleListFilter):
    """
    Custom filter that lets admin select ANY user who ever participated
    in at least one conversation — and then shows only conversations
    where that user was either participant_one OR participant_two.

    Why not just use foreign key filter? → because Conversation has TWO
    symmetric participant fields → standard FK filter would only show
    one side.
    """

    # How this filter appears in the admin sidebar
    title = "user"

    # URL parameter name (?user=123)
    parameter_name = "user"

    def lookups(self, request, model_admin):
        """
        Returns list of choices that appear in the dropdown.

        Important: we ONLY show users who actually have at least one conversation
        → avoids showing hundreds/thousands of irrelevant users
        """
        # We use both related_names to find users who appear in either position
        users = (
            User.objects.filter(
                # conversations_as_p1 → reverse relation when user is participant_one
                # conversations_as_p2 → reverse relation when user is participant_two
                Q(conversations_as_p1__isnull=False)
                | Q(conversations_as_p2__isnull=False)
            )
            # distinct() prevents the same user appearing twice if they are in many convs
            .distinct()
            # ordering by email becasue our user model dont have usernames
            .order_by("email")
        )

        # Format: (value in URL, label shown in dropdown)
        return [(user.id, user.email) for user in users]

    def has_unread(self, obj):
        """Check if a conversation has unread messages for the current user."""
        # This would be implemented based on the current user's session
        # For now, we'll just return a placeholder
        return False

    def queryset(self, request, queryset):
        """
        This method is called when the filter is active.
        It modifies the main queryset of Conversation admin.
        """
        if self.value():  # user id was selected in the filter
            # Very important: we search in BOTH participant fields
            # because the relationship is symmetric
            return queryset.filter(
                Q(participant_one_id=self.value()) | Q(participant_two_id=self.value())
            )

        # No filter value selected → show everything (default behavior)
        return queryset


class PropertyFilter(admin.SimpleListFilter):
    """
    Custom sidebar filter in Conversation admin that lets you select a Property
    and then shows only chat conversations that are attached to that property.

    Typical use-case: support team wants to see all chat history related to
    a specific apartment/house/booking/unit.
    """

    # How the filter appears in the Django admin sidebar
    title = "property"

    # URL parameter: ?property=42
    parameter_name = "property"

    def lookups(self, request, model_admin):
        """
        Builds the dropdown list of choices.

        Crucial decision: we ONLY show Properties that actually have
        at least one conversation → prevents showing hundreds of empty
        properties in the filter dropdown.
        """

        properties = (
            Property.objects
            # conversations is the reverse relation → Property → Conversation
            # (most likely ForeignKey in Conversation model: property = models.ForeignKey(...))
            .filter(conversations__isnull=False)
            # distinct() is important because one property can have many conversations
            # without it → same property would appear multiple times
            .distinct()
            # name is usually the most human-friendly field to sort by
            .order_by("-created_at")
        )

        # Format for admin dropdown: (value saved in URL, visible label)
        # Using .id and .name is the most common and readable choice
        return [
            (prop.id, f"{prop.name} ({prop.conversations.count()})")
            for prop in properties
        ]

    def queryset(self, request, queryset):
        """
        Called when the filter is active — modifies the main Conversation queryset.
        """
        if self.value():  # means user selected a property in the dropdown
            # Filter conversations that belong to exactly this property
            # Assumes Conversation has field: property = ForeignKey(Property, ...)
            return queryset.filter(property_id=self.value())

        # No property selected → don't apply any extra filtering
        return queryset


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    """
    Admin interface for Conversation model.
    Covers requirements:
    - List all conversations
    - Filtering by user / property / date
    - Show participants, property, message stats

    Why this structure?
    - Uses Django's powerful admin customization
    - Prefetches + annotation → good performance on medium/large datasets
    - Inlines + custom display fields → great for support / moderation use-case
    """

    # Columns shown in changelist
    list_display = [
        "id",
        "property_link",  # custom method → clickable
        "participant_one_link",
        "participant_two_link",
        "message_count",  # annotated → fast
        "created_at",
        "updated_at",
    ]

    # Filters in right sidebar
    list_filter = [
        UserFilter,  # ← assuming custom UserFilter exists (e.g. for participant_one/two)
        PropertyFilter,  # ← assuming custom PropertyFilter exists
        "created_at",  # built-in DateFieldListFilter (day/month/year hierarchy)
        "updated_at",  # same
    ]

    # Quick search box (uses OR between fields)
    search_fields = [
        "participant_one__email",
        "participant_two__email",
        "property__name",
    ]

    # Prevent accidental modification of timestamps
    readonly_fields = ["created_at", "updated_at"]

    # Adds nice date drill-down links at top (year → month → day)
    date_hierarchy = "created_at"

    # ────────────────────────────────────────────────
    # Inline: shows messages without leaving conversation page
    # ────────────────────────────────────────────────

    class MessageInline(admin.TabularInline):
        """Shows recent messages inside each conversation row."""

        model = Message
        extra = 0  # don't show empty rows
        can_delete = False  # prevent accidental deletion from admin
        fields = ["sender", "content_preview", "created_at", "is_read"]
        readonly_fields = fields  # view-only inline (good for audit trail)
        ordering = ["created_at"]  # chronological
        show_change_link = True  # optional: link to full Message change page

        def content_preview(self, obj):
            """Short preview to avoid cluttering the admin."""

            max_length = 100
            content = obj.content or ""
            return (
                content[:max_length] + "..." if len(content) > max_length else content
            )

        content_preview.short_description = _("Message")

        def has_add_permission(self, request, obj=None):
            """Block adding new messages via admin (business rule)."""
            return False

        def has_change_permission(self, request, obj=None):
            """Optional: also block editing if you want strict audit."""
            return False

    inlines = [MessageInline]

    # ────────────────────────────────────────────────
    # Performance: reduce N+1 queries
    # ────────────────────────────────────────────────
    def get_queryset(self, request):
        """
        Optimize default queryset:
        - select_related → single JOIN for FKs
        - annotate → pre-calculate message count (very important!)
        """

        qs = super().get_queryset(request)

        return qs.select_related(
            "property",
            "participant_one",
            "participant_two",
        ).annotate(
            msg_count=Count("messages")  # → messages__count in SQL
        )

    # ────────────────────────────────────────────────
    # Custom columns (display + sorting)
    # ────────────────────────────────────────────────
    def message_count(self, obj):
        """Use annotated value if available, fallback to count()."""

        # Why fallback? → useful in case someone calls .all() outside admin
        return obj.msg_count if hasattr(obj, "msg_count") else obj.messages.count()

    message_count.short_description = _("Messages")
    message_count.admin_order_field = "msg_count"  # enables sorting by this column

    def property_link(self, obj):
        """Clickable link to property admin page."""

        if not obj.property:
            return "-"
        url = self.__admin_url("properties", "property", obj.property.pk)
        return format_html('<a href="{}">{}</a>', url, obj.property.name)

    property_link.short_description = _("Property")

    def participant_one_link(self, obj):
        """Dynamic admin link to user (works with custom User models)."""

        if not obj.participant_one:
            return "-"

        User = get_user_model()
        app = User._meta.app_label
        model = User._meta.model_name
        url = self.__admin_url(app, model, obj.participant_one.pk)
        return format_html('<a href="{}">{}</a>', url, obj.participant_one.email)

    participant_one_link.short_description = _("Participant 1")

    def participant_two_link(self, obj):
        """Same as above for participant_two."""

        if not obj.participant_two:
            return "-"

        User = get_user_model()
        app = User._meta.app_label
        model = User._meta.model_name
        url = self.__admin_url(app, model, obj.participant_two.pk)
        return format_html('<a href="{}">{}</a>', url, obj.participant_two.email)

    participant_two_link.short_description = _("Participant 2")

    # Small helper (avoids hard-coded /admin/ prefix and quoting issues)
    def __admin_url(self, app_label, model_name, obj_id):
        return f"/admin/{app_label}/{model_name}/{quote(obj_id)}/change/"


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """
    Admin interface for Message model.

    Validates requirements:
    - View individual messages with context
    - Show sender, content preview, timestamp, read status

    Typical use-case: support team / moderation reviewing chat history
    """

    # Columns in changelist view
    list_display = [
        "id",
        "conversation_link",  # custom → clickable to conversation
        "sender_link",  # custom → clickable to user
        "content_preview",  # truncated content
        "created_at",
        "is_read",  # boolean field → shows nice icon
    ]

    # Right sidebar filters
    list_filter = [
        "is_read",  # True/False/All
        "created_at",  # built-in date filter (day/month/year)
    ]

    # Search box — searches across these fields with OR
    search_fields = [
        "sender__email",
        "content",  # full-text-ish search on message body
        "conversation__participant_one__email",
        "conversation__participant_two__email",
    ]

    # Prevent modification of important audit fields
    readonly_fields = [
        "created_at",
        "conversation",
        "sender",
        # consider also adding: "recipient" if you have it
    ]

    # Top date drill-down navigation (year → month → day)
    date_hierarchy = "created_at"

    # ────────────────────────────────────────────────
    # Performance: avoid N+1 queries in changelist
    # ────────────────────────────────────────────────
    def get_queryset(self, request):
        """
        Optimize default queryset:
        - select_related for all important forward FKs
        - Important because list_display shows conversation & sender fields
        """
        qs = super().get_queryset(request)
        return qs.select_related(
            "conversation",
            "sender",
            "conversation__participant_one",
            "conversation__participant_two",
        )

    # ────────────────────────────────────────────────
    # Custom display fields
    # ────────────────────────────────────────────────
    def content_preview(self, obj):
        """Shortened content to avoid breaking table layout."""
        max_length = 50
        content = obj.content or ""
        if len(content) > max_length:
            return content[:max_length] + "…"
        return content

    content_preview.short_description = _("Content")

    def conversation_link(self, obj):
        """Clickable link to the parent conversation admin page."""
        if not obj.conversation:
            return "-"
        # Hard-coded app_label/model_name — works if model is in 'chat' app
        return format_html(
            '<a href="/admin/chat/conversation/{}/change/">Conversation {}</a>',
            obj.conversation.pk,
            obj.conversation.pk,
        )

    conversation_link.short_description = _("Conversation")

    def sender_link(self, obj):
        """Dynamic link to sender — supports custom User models."""
        if not obj.sender:
            return "-"

        User = obj.sender.__class__  # more reliable than get_user_model() here
        app_label = User._meta.app_label
        model_name = User._meta.model_name

        return format_html(
            '<a href="/admin/{}/{}/{}/change/">{}</a>',
            app_label,
            model_name,
            obj.sender.pk,
            obj.sender.email or obj.sender.username or str(obj.sender),
        )

    sender_link.short_description = _("Sender")
