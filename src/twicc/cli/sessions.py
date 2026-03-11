"""CLI implementation for the ``twicc sessions`` subcommand."""

import sys

import orjson


def main(*, project: str | None = None, limit: int = 20, offset: int = 0, archived: bool = False) -> None:
    """List sessions as JSON to stdout."""
    import django

    django.setup()

    from twicc.core.models import Session
    from twicc.core.serializers import serialize_session

    qs = Session.objects.filter(
        type="session",
        created_at__isnull=False,
        user_message_count__gt=0,
    ).order_by("-mtime")

    if not archived:
        qs = qs.filter(archived=False)

    if project is not None:
        qs = qs.filter(project_id=project)

    sessions = qs[offset : offset + limit]
    data = [serialize_session(s) for s in sessions]

    sys.stdout.buffer.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))
    sys.stdout.buffer.write(b"\n")
