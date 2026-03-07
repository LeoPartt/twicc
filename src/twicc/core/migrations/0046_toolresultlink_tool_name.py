from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0045_agentlink_is_background_result_count"),
    ]

    operations = [
        migrations.AddField(
            model_name="toolresultlink",
            name="tool_name",
            field=models.CharField(default="", max_length=255),
        ),
        migrations.AddField(
            model_name="toolresultlink",
            name="tool_result_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddIndex(
            model_name="toolresultlink",
            index=models.Index(
                fields=["session", "tool_name"],
                name="idx_tool_result_link_by_name",
            ),
        ),
    ]
