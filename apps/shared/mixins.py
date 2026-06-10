from django.core.exceptions import PermissionDenied


class HTMXMixin:
    @property
    def is_htmx(self):
        return bool(self.request.htmx)


class OwnerRequiredMixin:
    owner_field = "user"

    def check_owner(self, obj):
        if getattr(obj, self.owner_field) != self.request.user:
            raise PermissionDenied
