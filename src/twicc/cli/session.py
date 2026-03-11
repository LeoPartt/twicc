"""CLI implementation for the ``twicc session`` subcommand."""

import sys

import orjson


def _get_session(session_id: str):
    """Fetch a valid session (created_at set, at least one user message) or exit."""
    from twicc.core.models import Session

    try:
        session = Session.objects.get(
            id=session_id,
            created_at__isnull=False,
            user_message_count__gt=0,
        )
    except Session.DoesNotExist:
        print(f"Error: session '{session_id}' not found.", file=sys.stderr)
        sys.exit(1)

    return session


def main(session_id: str) -> None:
    """Fetch a single session by ID and print its JSON representation to stdout."""
    import django

    django.setup()

    from twicc.core.serializers import serialize_session

    session = _get_session(session_id)
    data = serialize_session(session)

    sys.stdout.buffer.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))
    sys.stdout.buffer.write(b"\n")


def content(session_id: str, *, range_str: str) -> None:
    """Fetch session item(s) by line number or range and print as JSON to stdout."""
    import django

    django.setup()

    from twicc.core.models import SessionItem

    _get_session(session_id)

    # Parse range: either a single line number "42" or a range "10-20"
    if "-" in range_str:
        parts = range_str.split("-", 1)
        try:
            start, end = int(parts[0]), int(parts[1])
        except ValueError:
            print(f"Error: invalid range '{range_str}'. Use a number or start-end (e.g. '5' or '10-20').", file=sys.stderr)
            sys.exit(1)
        if start > end:
            print(f"Error: invalid range '{range_str}'. Start must be <= end.", file=sys.stderr)
            sys.exit(1)
        items = SessionItem.objects.filter(
            session_id=session_id, line_num__gte=start, line_num__lte=end
        ).order_by("line_num")
    else:
        try:
            line_num = int(range_str)
        except ValueError:
            print(f"Error: invalid line number '{range_str}'. Use a number or start-end (e.g. '5' or '10-20').", file=sys.stderr)
            sys.exit(1)
        items = SessionItem.objects.filter(session_id=session_id, line_num=line_num)

    # Parse each item's content string into real JSON objects
    data = [orjson.loads(item.content) for item in items]

    if not data:
        print("Error: no items found for the given range.", file=sys.stderr)
        sys.exit(1)

    sys.stdout.buffer.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))
    sys.stdout.buffer.write(b"\n")


def agents(session_id: str, *, limit: int = 20, offset: int = 0) -> None:
    """List subagents of a session as JSON to stdout."""
    import django

    django.setup()

    from twicc.core.models import Session
    from twicc.core.serializers import serialize_session

    session = _get_session(session_id)

    if session.parent_session_id is not None:
        print(f"Error: session '{session_id}' is a subagent, not a parent session.", file=sys.stderr)
        sys.exit(1)

    subagents = Session.objects.filter(parent_session_id=session_id).order_by("-mtime")[offset : offset + limit]
    data = [serialize_session(s) for s in subagents]

    sys.stdout.buffer.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))
    sys.stdout.buffer.write(b"\n")
