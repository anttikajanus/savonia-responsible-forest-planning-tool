"""Prepare an increasing minor version, or restore this source's release on retry."""

import argparse
from configparser import ConfigParser
from dataclasses import dataclass
import os
from pathlib import Path
import re
import subprocess


METADATA = Path("qgis_plugin/savonia_responsible_forest_planning_tool/metadata.txt")
VERSION = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)")


def git(root, *arguments):
    return subprocess.run(
        ["git", *arguments], cwd=root, check=True, capture_output=True,
        text=True, encoding="utf-8",
    ).stdout.strip()


def metadata_version(content):
    parser = ConfigParser(interpolation=None)
    parser.read_string(content)
    value = parser["general"]["version"]
    if not VERSION.fullmatch(value):
        raise ValueError(f"Expected a major.minor.patch metadata version, got {value!r}")
    return tuple(map(int, value.split(".")))


@dataclass(frozen=True)
class Release:
    version: str
    existing: bool

    @property
    def tag(self):
        return f"v{self.version}"


def prepare_release(root):
    """Tags contain release commits with the original source commit as sole parent."""
    source = git(root, "rev-parse", "HEAD")
    metadata_path = root / METADATA
    content = metadata_path.read_text(encoding="utf-8")
    base = metadata_version(content)
    tags = {}
    for tag in git(root, "tag", "--list", "v*").splitlines():
        if VERSION.fullmatch(tag[1:]):
            version = tuple(map(int, tag[1:].split(".")))
            if version[0] == base[0]:
                tags[version] = tag

    for version, tag in sorted(tags.items(), reverse=True):
        reference = f"refs/tags/{tag}"
        if (git(root, "show", "-s", "--format=%P", reference) == source
                and git(root, "show", "-s", "--format=%s", reference) == f"Release {tag}"
                and metadata_version(git(root, "show", f"{reference}:{METADATA.as_posix()}")) == version):
            git(root, "checkout", "--detach", reference)
            return Release(tag[1:], existing=True)

    latest = max([base, *tags])
    version = f"{base[0]}.{latest[1] + 1}.0"
    content, count = re.subn(r"(?m)^version=[^\r\n]*", f"version={version}", content)
    if count != 1:
        raise ValueError("Expected exactly one version= line in metadata.txt")
    metadata_path.write_text(content, encoding="utf-8", newline="\n")
    return Release(version, existing=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=os.environ.get("GITHUB_OUTPUT"))
    args = parser.parse_args()
    release = prepare_release(Path.cwd())
    outputs = (f"version={release.version}\ntag={release.tag}\n"
               f"existing={str(release.existing).lower()}\n")
    if args.output:
        with args.output.open("a", encoding="utf-8") as output:
            output.write(outputs)
    print(outputs, end="")


if __name__ == "__main__":
    main()
