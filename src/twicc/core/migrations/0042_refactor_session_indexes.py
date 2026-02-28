# Refactor Session indexes and recompute project sessions_count.
#
# 1. Replace two separate indexes (project+mtime, project+type) with:
#    - A combined (project, type, -mtime) index for all queries
#    - A conditional (project, -mtime) index for API/visible sessions only
# 2. Recompute sessions_count to exclude sessions without user messages.

from django.db import migrations, models


def recompute_sessions_count(apps, schema_editor):
    """Recompute sessions_count on all projects, now excluding sessions without user messages."""
    Project = apps.get_model("core", "Project")
    Session = apps.get_model("core", "Session")
    for project in Project.objects.all():
        project.sessions_count = Session.objects.filter(
            project=project,
            type="session",
            created_at__isnull=False,
            user_message_count__gt=0,
        ).count()
        project.save(update_fields=["sessions_count"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0041_delete_empty_projects"),
    ]

    operations = [
        # Remove old indexes
        migrations.RemoveIndex(
            model_name="session",
            name="idx_session_project_mtime",
        ),
        migrations.RemoveIndex(
            model_name="session",
            name="idx_session_project_type",
        ),
        # Add new combined index
        migrations.AddIndex(
            model_name="session",
            index=models.Index(
                fields=["project", "type", "-mtime"],
                name="idx_session_project_type_mtime",
            ),
        ),
        # Add conditional index for visible sessions (API + counts)
        migrations.AddIndex(
            model_name="session",
            index=models.Index(
                fields=["project", "-mtime"],
                name="idx_session_visible",
                condition=models.Q(
                    user_message_count__gt=0,
                    type="session",
                    created_at__isnull=False,
                ),
            ),
        ),
        # Recompute sessions_count with the new filter
        migrations.RunPython(
            recompute_sessions_count,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
