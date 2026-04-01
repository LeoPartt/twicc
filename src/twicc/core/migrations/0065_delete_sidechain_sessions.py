"""Delete sidechain sessions (context compaction and title suggestions).

The subagents/ directory contains sidechain files alongside real subagent files:
- agent-a<hex>.jsonl — real subagents (Task tool), kept
- agent-acompact-<hex>.jsonl — context compaction, deleted
- agent-aprompt_suggestion-<hex>.jsonl — title suggestions, deleted

These sidechain sessions were previously ingested as regular subagents because
the file filter only checked for the "agent-" prefix. Now that the filter uses
a strict regex (agent-a[0-9a-f]+.jsonl), we clean up already-ingested ones.
"""

from django.db import migrations
from django.db.models import Q


def delete_sidechain_sessions(apps, schema_editor):
    Session = apps.get_model("core", "Session")

    # Find all sidechain sessions by their known prefixes.
    # Real subagents have agent_id like "a6c7d21" (pure hex), sidechains have
    # "acompact-<hex>" or "aprompt_suggestion-<hex>".
    sidechain_sessions = Session.objects.filter(
        type="subagent",
    ).filter(
        Q(agent_id__startswith="acompact-") | Q(agent_id__startswith="aprompt_suggestion-")
    )

    count = sidechain_sessions.count()
    if count == 0:
        return

    # Django CASCADE handles related SessionItem, ToolResultLink, and AgentLink rows.
    # (ProcessRun/SessionCron use plain CharField, not FK, but sidechains never appear there.)
    deleted_total, deleted_per_model = sidechain_sessions.delete()

    details = ", ".join(f"{model}: {n}" for model, n in deleted_per_model.items())
    print(f"\n  Deleted {count} sidechain sessions ({details})")


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0064_custom_title_debug_only"),
    ]

    operations = [
        migrations.RunPython(delete_sidechain_sessions, migrations.RunPython.noop),
    ]
