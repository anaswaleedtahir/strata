from django.db.models import Count, Q

from apps.properties.models import Favorite, Property

PROPERTY_ORDERINGS = {
    "newest": ("-created_at", "-id"),
    "oldest": ("created_at", "id"),
    "price_asc": ("price", "id"),
    "price_desc": ("-price", "id"),
}


def property_list_published(
    *,
    user=None,
    show_favorites: bool = False,
    show_my_properties: bool = False,
    query: str = "",
    property_type: str = "",
    min_price=None,
    max_price=None,
    bedrooms=None,
    bathrooms=None,
    ordering: str = "newest",
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

    query = query.strip()
    if query:
        qs = qs.filter(
            Q(name__icontains=query)
            | Q(full_address__icontains=query)
            | Q(description__icontains=query)
        )
    if property_type:
        qs = qs.filter(property_type=property_type)
    if min_price is not None:
        qs = qs.filter(price__gte=min_price)
    if max_price is not None:
        qs = qs.filter(price__lte=max_price)
    if bedrooms is not None:
        qs = qs.filter(bedrooms__gte=bedrooms)
    if bathrooms is not None:
        qs = qs.filter(bathrooms__gte=bathrooms)

    return qs.order_by(*PROPERTY_ORDERINGS.get(ordering, PROPERTY_ORDERINGS["newest"]))


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


def property_counts_for_user(*, user) -> dict[str, int]:
    return Property.objects.filter(user=user).aggregate(
        total=Count("id"),
        published=Count("id", filter=Q(is_published=True)),
        drafts=Count("id", filter=Q(is_published=False)),
    )


def favorite_ids_for_user(*, user) -> set:
    return set(Favorite.objects.filter(user=user).values_list("property_id", flat=True))


def favorite_exists(*, user, property_obj: Property) -> bool:
    return Favorite.objects.filter(user=user, property=property_obj).exists()
