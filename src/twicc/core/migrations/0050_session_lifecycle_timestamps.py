from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0049_add_started_at_to_agent_link"),
    ]

    operations = [
        migrations.AddField(
            model_name="session",
            name="last_started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="session",
            name="last_updated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="session",
            name="last_stopped_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
