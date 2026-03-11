"""CLI implementation for the ``twicc projects`` subcommand."""

import sys

import orjson


def main(*, limit: int = 20, offset: int = 0, archived: bool = False) -> None:
    """List all projects as JSON to stdout."""
    import django

    django.setup()

    from twicc.core.models import Project
    from twicc.core.serializers import serialize_project

    qs = Project.objects.order_by("-mtime")

    if not archived:
        qs = qs.filter(archived=False)

    projects = qs[offset : offset + limit]
    data = [serialize_project(p) for p in projects]

    sys.stdout.buffer.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))
    sys.stdout.buffer.write(b"\n")
