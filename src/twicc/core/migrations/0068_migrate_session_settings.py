"""Migrate session settings to the new null-based default model.

1. Make claude_in_chrome and context_max nullable (they had hardcoded defaults before).
2. Data migration: convert keep_settings-based logic to null (= follow global default)
   vs explicit value (= forced for this session).
3. Remove keep_settings field.

Sessions with keep_settings=True: compare each setting to the global default from
settings.json — set to NULL if it matches the default, keep the value otherwise.
Sessions with keep_settings=False: set all settings to NULL (follow global defaults).
"""

import json
import os
from pathlib import Path

from django.db import migrations, models

# Hardcoded fallbacks (used only if settings.json is missing or unreadable)
_FALLBACK_DEFAULTS = {
    "defaultPermissionMode": "default",
    "defaultModel": "opus",
    "defaultEffort": "medium",
    "defaultThinking": True,
    "defaultClaudeInChrome": True,
    "defaultContextMax": 200_000,
}

# Mapping: session field → settings.json key
_FIELD_TO_SETTINGS_KEY = {
    "permission_mode": "defaultPermissionMode",
    "selected_model": "defaultModel",
    "effort": "defaultEffort",
    "thinking_enabled": "defaultThinking",
    "claude_in_chrome": "defaultClaudeInChrome",
    "context_max": "defaultContextMax",
}


def _read_defaults():
    """Read global defaults from settings.json without importing project code."""
    env_value = os.environ.get("TWICC_DATA_DIR", "").strip()
    data_dir = Path(env_value).resolve() if env_value else Path.home() / ".twicc"
    settings_path = data_dir / "settings.json"
    try:
        file_data = json.loads(settings_path.read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        file_data = {}
    return {
        field: file_data.get(key, _FALLBACK_DEFAULTS[key])
        for field, key in _FIELD_TO_SETTINGS_KEY.items()
    }


def forwards(apps, schema_editor):
    Session = apps.get_model("core", "Session")
    defaults = _read_defaults()
    setting_fields = list(_FIELD_TO_SETTINGS_KEY.keys())

    # Bulk update: non-pinned sessions → all settings to NULL
    Session.objects.filter(keep_settings=False).update(
        **{field: None for field in setting_fields}
    )

    # Pinned sessions: null out settings that match the global default
    for session in Session.objects.filter(keep_settings=True).iterator():
        update_fields = []
        for field in setting_fields:
            if getattr(session, field) == defaults[field]:
                setattr(session, field, None)
                update_fields.append(field)
        if update_fields:
            session.save(update_fields=update_fields)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0067_session_keep_settings"),
    ]

    operations = [
        # 1. Make claude_in_chrome and context_max nullable FIRST
        #    (so the data migration can set them to NULL)
        migrations.AlterField(
            model_name="session",
            name="claude_in_chrome",
            field=models.BooleanField(null=True, default=None),
        ),
        migrations.AlterField(
            model_name="session",
            name="context_max",
            field=models.PositiveIntegerField(null=True, default=None),
        ),
        # 2. Data migration (needs keep_settings to still exist)
        migrations.RunPython(forwards, migrations.RunPython.noop),
        # 3. Remove keep_settings
        migrations.RemoveField(
            model_name="session",
            name="keep_settings",
        ),
    ]
