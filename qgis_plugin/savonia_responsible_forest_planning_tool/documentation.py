"""Resolve packaged help without QGIS, widgets, or network access."""

from configparser import ConfigParser, Error as ConfigError
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote


class ResourceError(ValueError):
    """A packaged resource cannot be used; adapters translate a corrective message."""

    def __init__(self, resource, path, reason):
        self.resource = resource
        self.path = str(path)
        self.reason = reason
        super().__init__(f"Documentation resource {resource!r}: {reason} ({path})")


class _Anchors(HTMLParser):
    def __init__(self):
        super().__init__()
        self.anchors = set()

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name == "id" or (tag == "a" and name == "name"):
                self.anchors.add(value)


def _read(resource, path):
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ResourceError(resource, path, "unreadable") from error


def manual_url(language, section="workflow", package_root=None):
    """Return a local browser URL for an explicitly selected manual language."""
    root = Path(package_root) if package_root is not None else Path(__file__).parent
    if language not in ("fi", "en"):
        raise ResourceError("manual", root, "unsupported_language")
    path = root / "docs" / "help" / f"manual_{language}.html"
    if package_root is None:
        # Source-linked development uses the repository's canonical manuals.
        checkout = root.resolve().parents[1]
        if (checkout / "qgis_plugin" / "package.ps1").is_file():
            path = checkout / "docs" / "help" / path.name
    parser = _Anchors()
    parser.feed(_read("manual", path))
    if section not in parser.anchors:
        raise ResourceError("manual", path, "missing_section")
    return path.resolve().as_uri() + "#" + quote(section, safe="")


def resource_url(resource, package_root=None):
    """Return a validated local URL for a packaged legal/credit resource."""
    root = Path(package_root) if package_root is not None else Path(__file__).parent
    filenames = {"licence": "LICENSE", "notices": "THIRD_PARTY_NOTICES",
                 "inventory": "COMPONENT_INVENTORY.txt"}
    if resource not in filenames:
        raise ResourceError(resource, root, "unknown_resource")
    path = root / filenames[resource]
    _read(resource, path)
    return path.resolve().as_uri()


def metadata(package_root=None):
    """Read authoritative installed identity and links; never invent a version."""
    root = Path(package_root) if package_root is not None else Path(__file__).parent
    path = root / "metadata.txt"
    text = _read("metadata", path)
    parser = ConfigParser(interpolation=None)
    parser.optionxform = str
    try:
        parser.read_string(text)
        result = dict(parser["general"])
        if not result.get("name", "").strip() or not result.get("version", "").strip():
            raise ValueError("Missing name or version")
    except (ConfigError, KeyError, ValueError) as error:
        raise ResourceError("metadata", path, "invalid_metadata") from error
    return result
