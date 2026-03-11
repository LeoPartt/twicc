"""CLI implementation for the ``twicc project`` subcommand."""

import sys

import orjson


def main(project_id: str) -> None:
    """Fetch a single project by ID and print its JSON representation to stdout."""
    import django

    django.setup()

    from twicc.core.models import Project
    from twicc.core.serializers import serialize_project

    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        print(f"Error: project '{project_id}' not found.", file=sys.stderr)
        sys.exit(1)

    data = serialize_project(project)

    sys.stdout.buffer.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))
    sys.stdout.buffer.write(b"\n")
