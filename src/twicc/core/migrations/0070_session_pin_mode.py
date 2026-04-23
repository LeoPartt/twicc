"""Convert session `pinned` from BooleanField to CharField with PinMode choices.

Existing pinned=True sessions become pinned='project' (preserves current behavior:
pin is scoped to the session's own project filter). Unpinned sessions become NULL.

Strategy (SQLite-safe):
1. Add a new `pin_mode` CharField (nullable).
2. Data migration: copy pinned=True → pin_mode='project'.
3. Remove the old `pinned` BooleanField.
4. Rename `pin_mode` → `pinned` so the final column matches the model.
"""

from django.db import migrations, models


def migrate_pinned_to_pin_mode(apps, schema_editor):
    Session = apps.get_model("core", "Session")
    Session.objects.filter(pinned=True).update(pin_mode="project")


def reverse_pin_mode_to_pinned(apps, schema_editor):
    Session = apps.get_model("core", "Session")
    Session.objects.filter(pin_mode__isnull=False).update(pinned=True)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0069_session_compacted"),
    ]

    operations = [
        migrations.AddField(
            model_name="session",
            name="pin_mode",
            field=models.CharField(
                max_length=16,
                choices=[
                    ("project", "Project"),
                    ("workspace", "Workspace"),
                    ("all", "All projects"),
                ],
                null=True,
                blank=True,
                default=None,
            ),
        ),
        migrations.RunPython(migrate_pinned_to_pin_mode, reverse_pin_mode_to_pinned),
        migrations.RemoveField(
            model_name="session",
            name="pinned",
        ),
        migrations.RenameField(
            model_name="session",
            old_name="pin_mode",
            new_name="pinned",
        ),
    ]
