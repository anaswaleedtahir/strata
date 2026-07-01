"""Backfill Property.thumbnail from each property's existing primary image.

- For every property without a thumbnail, reuse its primary image (or, if none is
  flagged primary, its first image) by referencing the same stored file. No file
  copy is performed: the thumbnail simply points at the existing image's path.
- Any *published* property that still has no usable image is reverted to a draft
  (is_published=False) so it cannot appear publicly without a thumbnail.
"""

from django.db import migrations


def backfill_thumbnails(apps, schema_editor):
    Property = apps.get_model("properties", "Property")

    for prop in Property.objects.all():
        if prop.thumbnail:
            continue

        primary = (
            prop.images.filter(is_primary=True).first() or prop.images.first()
        )
        if primary and primary.image:
            # Reference the same stored file; ImageField only persists the path.
            prop.thumbnail.name = primary.image.name
            prop.save(update_fields=["thumbnail"])
        elif prop.is_published:
            prop.is_published = False
            prop.save(update_fields=["is_published"])


def noop_reverse(apps, schema_editor):
    # Backfill is not reversible; clearing thumbnails would lose data.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("properties", "0010_property_thumbnail"),
    ]

    operations = [
        migrations.RunPython(backfill_thumbnails, noop_reverse),
    ]
