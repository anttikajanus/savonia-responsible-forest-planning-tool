"""Shared serialization helpers for result and provenance adapters."""

import json


def json_default(value):
    """Convert Qt and date-like values passed to ``json.dumps``."""
    if hasattr(value, "toString"):
        try:
            return value.toString()
        except Exception:
            pass
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    return str(value)


def stringify(value, ensure_ascii=False):
    """Serialize structured values and preserve the existing blank/null policy."""
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=ensure_ascii, sort_keys=True)
    return str(value)
