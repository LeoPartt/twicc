"""CLI implementation for the ``twicc search`` subcommand."""

import sys


def main(query: str, *, limit: int = 20, offset: int = 0) -> None:
    """Execute a raw Tantivy search and print JSON results to stdout."""
    from twicc.search import raw_search

    try:
        result = raw_search(query, limit=limit, offset=offset)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(result)
