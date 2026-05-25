from apps.properties.models import Favorite, Property


def property_list_published(
    *, user=None, show_favorites: bool = False, show_my_properties: bool = False
):
    qs = Property.published.all().select_related("user").prefetch_related("images")

    if user is not None and user.is_authenticated:
        if show_favorites:
            favorited_ids = Favorite.objects.filter(user=user).values_list(
                "property_id", flat=True
            )
            qs = qs.filter(id__in=favorited_ids)
        if show_my_properties:
            qs = qs.filter(user=user)

    return qs


def property_get_with_related(*, pk: int):
    return (
        Property.objects.select_related("user")
        .prefetch_related("images")
        .filter(pk=pk)
        .first()
    )


def property_list_favorites_for_user(*, user):
    return (
        Property.objects.filter(favorited_by__user=user)
        .distinct()
        .select_related("user")
        .prefetch_related("images")
    )


def property_list_for_user(*, user):
    return (
        Property.objects.filter(user=user)
        .select_related("user")
        .prefetch_related("images")
    )


def favorite_ids_for_user(*, user) -> set:
    return set(Favorite.objects.filter(user=user).values_list("property_id", flat=True))


def favorite_exists(*, user, property_obj: Property) -> bool:
    return Favorite.objects.filter(user=user, property=property_obj).exists()
