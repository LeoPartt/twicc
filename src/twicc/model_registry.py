"""
Registry of supported Claude model versions.

Each model family (opus, sonnet) has one ``latest`` version and zero or more
older versions with a retirement date.  The ``selected_model`` value stored in
settings and session DB fields uses:
- bare alias for latest: ``"opus"``, ``"sonnet"``
- versioned alias for non-latest: ``"opus-4.5"``, ``"sonnet-4.5"``

When communicating with the SDK, latest aliases are passed as-is (the CLI
resolves them), while versioned aliases are resolved to their ``full_name``.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import NamedTuple

logger = logging.getLogger(__name__)


class ModelVersion(NamedTuple):
    """A single supported model version."""

    model: str  # Family alias: "opus", "sonnet"
    version: str  # Short version: "4.6", "4.5"
    full_name: str  # Full SDK model ID: "claude-opus-4-6"
    retirement_date: date | None  # Date after which this version is retired (None for latest)
    latest: bool  # True = current default for this family (unique per model)
    supports_1m: bool  # Whether extended 1M context is available


MODEL_VERSIONS: list[ModelVersion] = [
    ModelVersion("opus", "4.6", "claude-opus-4-6", retirement_date=None, latest=True, supports_1m=True),
    ModelVersion("opus", "4.5", "claude-opus-4-5-20251101", retirement_date=date(2026, 11, 24), latest=False, supports_1m=False),
    ModelVersion("sonnet", "4.6", "claude-sonnet-4-6", retirement_date=None, latest=True, supports_1m=True),
    ModelVersion("sonnet", "4.5", "claude-sonnet-4-5-20250929", retirement_date=date(2026, 9, 29), latest=False, supports_1m=False),
]


def _parse_version(version_str: str) -> list[int]:
    """Parse a version string like "4.5" into a list of ints [4, 5]."""
    return [int(p) for p in version_str.split(".")]


def get_model_version(selected_model: str) -> ModelVersion | None:
    """Look up a ModelVersion by its selected_model value.

    Accepts both bare aliases ("opus") and versioned aliases ("opus-4.5").
    For bare aliases, returns the latest version of that family.
    """
    if "-" in selected_model:
        model, version = selected_model.split("-", 1)
        for mv in MODEL_VERSIONS:
            if mv.model == model and mv.version == version:
                return mv
        return None

    for mv in MODEL_VERSIONS:
        if mv.model == selected_model and mv.latest:
            return mv
    return None


def resolve_sdk_model(selected_model: str | None, context_max: int) -> str | None:
    """Resolve a selected_model + context_max to the string to pass to the SDK.

    - Latest models ("opus", "sonnet"): pass the bare alias (CLI resolves it).
    - Versioned models ("opus-4.5"): pass the full_name from the registry.
    - Appends "[1m]" suffix when context_max is 1M and the model supports it.

    Returns None if selected_model is None or empty.
    """
    if not selected_model:
        return None

    mv = get_model_version(selected_model)
    if mv is None:
        logger.warning("Unknown model '%s', passing through to SDK", selected_model)
        base = selected_model
        supports_1m = True
    elif mv.latest:
        base = mv.model
        supports_1m = mv.supports_1m
    else:
        base = mv.full_name
        supports_1m = mv.supports_1m

    if context_max == 1_000_000 and supports_1m:
        return f"{base}[1m]"
    return base


def is_model_retired(selected_model: str) -> bool:
    """Check if a selected_model value refers to a retired version.

    Latest versions (retirement_date=None) are never considered retired.
    """
    mv = get_model_version(selected_model)
    if mv is None or mv.retirement_date is None:
        return False
    return date.today() > mv.retirement_date


def get_upgrade_target(selected_model: str) -> str | None:
    """Find the next version up for a retired model.

    Returns the selected_model value of the closest higher version in the same
    family.  If the next higher version is the latest, returns the bare alias.
    Returns None if no upgrade is possible.
    """
    mv = get_model_version(selected_model)
    if mv is None:
        return None

    family = sorted(
        [v for v in MODEL_VERSIONS if v.model == mv.model],
        key=lambda v: _parse_version(v.version),
    )

    current_parts = _parse_version(mv.version)
    for candidate in family:
        if _parse_version(candidate.version) > current_parts:
            return candidate.model if candidate.latest else f"{candidate.model}-{candidate.version}"

    return None


def get_all_selected_model_values() -> list[str]:
    """Return all valid selected_model values (for validation)."""
    result = []
    for mv in MODEL_VERSIONS:
        if mv.latest:
            result.append(mv.model)
        else:
            result.append(f"{mv.model}-{mv.version}")
    return result


def selected_model_supports_1m(selected_model: str | None) -> bool:
    """Check if a selected_model value supports 1M context.

    None means "use default" — caller should resolve to effective model first.
    Unknown models are assumed to support 1M (backward compat).
    """
    if not selected_model:
        return True
    mv = get_model_version(selected_model)
    if mv is None:
        return True
    return mv.supports_1m


def enforce_1m_consistency(selected_model: str | None, context_max: int) -> int:
    """If the model doesn't support 1M, cap context_max to 200K.

    Returns the (possibly adjusted) context_max value.
    """
    if context_max == 1_000_000 and not selected_model_supports_1m(selected_model):
        return 200_000
    return context_max


def serialize_model_registry() -> list[dict]:
    """Serialize the registry for the frontend bootstrap API.

    Returns a list of dicts sorted for dropdown display:
    latest versions first (sorted by model name), then non-latest sorted by
    version descending then model name.
    """
    latest = []
    non_latest = []
    for mv in MODEL_VERSIONS:
        entry = {
            "model": mv.model,
            "version": mv.version,
            "selectedModel": mv.model if mv.latest else f"{mv.model}-{mv.version}",
            "retirementDate": mv.retirement_date.isoformat() if mv.retirement_date else None,
            "latest": mv.latest,
            "supports1m": mv.supports_1m,
        }
        if mv.latest:
            latest.append(entry)
        else:
            non_latest.append(entry)

    latest.sort(key=lambda e: e["model"])
    non_latest.sort(key=lambda e: ([-int(p) for p in e["version"].split(".")], e["model"]))

    return latest + non_latest
