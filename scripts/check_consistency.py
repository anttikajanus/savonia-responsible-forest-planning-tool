"""Check repository documentation links and distribution configuration offline."""

import argparse
from collections import Counter
from configparser import ConfigParser, Error as ConfigError
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt
import yaml


ROOT = Path(__file__).resolve().parents[1]
METADATA = "qgis_plugin/savonia_responsible_forest_planning_tool/metadata.txt"
WORKFLOW = ".github/workflows/build-and-release.yml"
RULESET = ".github/rulesets/main-quality.json"
RUNTIMES = "scripts/qgis-runtimes.json"
REFERENCES = "docs/references/service-metadata"
VERSION_DOCUMENTS = ("README.md", "qgis_plugin/README.md", "docs/architecture/development.md",
                     "docs/help/manual_en.html", "docs/help/manual_fi.html")


class Document(HTMLParser):
    """Extract rendered links, explicit anchors and GitHub-style heading anchors."""

    def __init__(self, text, markdown=False):
        super().__init__()
        self.links = []
        self.anchors = set()
        self.heading = None
        self.text = []
        self.slugs = set()
        self.markdown = markdown
        if markdown:
            text = MarkdownIt("commonmark").enable("table").render(text)
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        for key in (("id", "name") if tag == "a" else ("id",)):
            if attributes.get(key):
                self.anchors.add(attributes[key])
        for key in ("href", "src"):
            if attributes.get(key):
                self.links.append(attributes[key])
        if self.markdown and re.fullmatch("h[1-6]", tag):
            self.heading = []
        if self.heading is not None and tag == "img":
            self.heading.append(attributes.get("alt", ""))

    def handle_data(self, data):
        self.text.append(data)
        if self.heading is not None:
            self.heading.append(data)

    def handle_endtag(self, tag):
        if self.heading is not None and re.fullmatch("h[1-6]", tag):
            # GitHub retains Unicode letters/numbers, spaces, underscores and hyphens.
            base = re.sub(r"[^\w\- ]", "", "".join(self.heading).lower()).replace(" ", "-")
            slug = base
            suffix = 0
            while slug in self.slugs:
                suffix += 1
                slug = f"{base}-{suffix}"
            self.slugs.add(slug)
            self.anchors.add(slug)
            self.heading = None


def repository_files(root):
    """Include maintained files, never ignored caches or local working records."""
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=root, capture_output=True, check=True,
    )
    return {Path(name) for name in result.stdout.decode("utf-8").split("\0") if name}


def documentation_errors(root, files):
    root = root.resolve()
    maintained = {root / path for path in files}
    directories = {parent for path in maintained for parent in path.parents if parent.is_relative_to(root)}
    manifest = json.loads((root / REFERENCES / "manifest.json").read_text(encoding="utf-8"))
    cached = {(root / REFERENCES / entry["path"]).resolve() for entry in manifest}
    documents = {}
    errors = []

    def document(path):
        if path not in documents:
            documents[path] = Document(path.read_text(encoding="utf-8"), path.suffix.lower() == ".md")
        return documents[path]

    for path in sorted(maintained):
        if path.suffix.lower() != ".md":
            continue
        for href in document(path).links:
            url = urlsplit(href)
            if url.scheme or url.netloc:
                continue
            target = (path.parent / unquote(url.path)).resolve() if url.path else path
            problem = None
            if not target.is_relative_to(root):
                problem = "target leaves the repository"
            elif target in cached and not url.fragment:
                # The manifest owns optional downloads, even in a fresh checkout.
                continue
            elif target in directories:
                if url.fragment:
                    target = target / "README.md"
                else:
                    continue
            if problem is None:
                if target not in maintained or not target.is_file():
                    problem = "missing maintained target"
                elif url.fragment:
                    if target.suffix.lower() not in (".md", ".html", ".htm"):
                        problem = "cannot validate anchor in this file type"
                    elif unquote(url.fragment) not in document(target).anchors:
                        problem = f"missing anchor #{unquote(url.fragment)}"
            if problem:
                errors.append(f"{path.relative_to(root).as_posix()}: {href}: {problem}")
    return errors


def version_parts(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d+\.\d+(?:\.\d+)?", value):
        raise ValueError(f"invalid QGIS version {value!r}")
    parts = tuple(map(int, value.split(".")))
    return parts + (0,) * (3 - len(parts))


def configuration_errors(metadata, workflow, ruleset, runtime_manifest=None):
    """Compare independent configuration owners, without a previous Git revision."""
    errors = []

    def require(condition, message):
        if not condition:
            errors.append(message)

    minimum = version_parts(metadata["qgisMinimumVersion"])
    maximum = version_parts(metadata["qgisMaximumVersion"])
    require(minimum <= maximum, f"{METADATA}: minimum exceeds maximum")
    require(re.fullmatch(r"\d+\.\d+\.\d+", metadata["version"]), f"{METADATA}: invalid plugin version")
    jobs = workflow["jobs"]
    quality = jobs["quality"]
    matrix = quality["strategy"]["matrix"]
    require(set(matrix) == {"qgis"}, f"{WORKFLOW}: expected one qgis matrix axis; update name expansion for new axes")
    baselines = matrix["qgis"]
    if isinstance(baselines, str):
        require(baselines == "${{ fromJSON(needs.build.outputs.qgis-runtimes) }}",
                f"{WORKFLOW}: unsupported QGIS matrix expression {baselines!r}")
        if runtime_manifest is None:
            raise ValueError(f"{RUNTIMES}: runtime manifest is required for the QGIS matrix")
        require(jobs["build"]["outputs"]["qgis-runtimes"] == "${{ steps.runtimes.outputs.matrix }}",
                f"{WORKFLOW}: QGIS matrix must use the shared runtime output")
        baselines = runtime_manifest["runtimes"]
        require(runtime_manifest["default_version"] in [item["version"] for item in baselines],
                f"{RUNTIMES}: default_version must name a baseline")
    versions = [version_parts(item["version"]) for item in baselines]
    require(bool(versions), f"{WORKFLOW}: empty QGIS matrix")
    require(len(set(versions)) == len(versions), f"{WORKFLOW}: duplicate QGIS baseline")
    require(minimum in versions, f"{WORKFLOW}: QGIS matrix must exercise metadata minimum {metadata['qgisMinimumVersion']}")
    for item, version in zip(baselines, versions):
        prefix = f"{WORKFLOW}: QGIS {item['version']}"
        require(minimum <= version <= maximum, f"{prefix} is outside the metadata installation range")
        major, minor, patch = version
        require(item["version_int"] == major * 10000 + minor * 100 + patch,
                f"{prefix}: version_int disagrees with version")
        require(re.fullmatch(rf"QGIS-OSGeo4W-{re.escape(item['version'])}-\d+\.msi", item["installer"]),
                f"{prefix}: installer disagrees with version")
        require(re.fullmatch(r"[a-fA-F0-9]{64}", item["sha256"]), f"{prefix}: invalid SHA-256")

    names = [jobs["build"]["name"]] + [
        quality["name"].replace("${{ matrix.qgis.version }}", item["version"]) for item in baselines
    ]
    require(all("${{" not in name for name in names), f"{WORKFLOW}: unresolved required job name expression")
    require(len(set(names)) == len(names), f"{WORKFLOW}: duplicate required job name")
    status_rules = [rule for rule in ruleset["rules"] if rule["type"] == "required_status_checks"]
    require(len(status_rules) == 1, f"{RULESET}: expected one required_status_checks rule")
    if len(status_rules) == 1:
        required = [item["context"] for item in status_rules[0]["parameters"]["required_status_checks"]]
        require(Counter(names) == Counter(required),
                f"{RULESET}: required checks disagree with {WORKFLOW}; expected {sorted(names)}, got {sorted(required)}")
    release = jobs["release"]
    dependencies = release["needs"]
    if isinstance(dependencies, str):
        dependencies = [dependencies]
    require(set(dependencies) == {"build", "quality"}, f"{WORKFLOW}: release must depend on build and quality")
    concurrency = release["concurrency"]
    require(isinstance(concurrency.get("group"), str) and bool(concurrency["group"])
            and "${{" not in concurrency["group"], f"{WORKFLOW}: release needs a shared static concurrency group")
    require(concurrency.get("cancel-in-progress") is False and concurrency.get("queue") == "max",
            f"{WORKFLOW}: release allocation must queue all runs without cancellation")
    return errors


def documented_minimum_errors(root, metadata):
    errors = []
    minimum = version_parts(metadata["qgisMinimumVersion"])
    for name in VERSION_DOCUMENTS:
        document = Document((root / name).read_text(encoding="utf-8"), name.endswith(".md"))
        # These entry points introduce the installation minimum before runtime examples.
        match = re.search(r"\bQGIS(?:-versiota)?\s+(\d+\.\d+(?:\.\d+)?)", "".join(document.text))
        if not match or version_parts(match[1]) != minimum:
            errors.append(f"{name}: documented QGIS minimum must agree with {METADATA}: {metadata['qgisMinimumVersion']}")
    return errors


def check_repository(root=ROOT):
    parser = ConfigParser(interpolation=None)
    parser.read_string((root / METADATA).read_text(encoding="utf-8"))
    workflow = yaml.safe_load((root / WORKFLOW).read_text(encoding="utf-8"))
    ruleset = json.loads((root / RULESET).read_text(encoding="utf-8"))
    runtime_manifest = json.loads((root / RUNTIMES).read_text(encoding="utf-8"))
    return (documentation_errors(root, repository_files(root))
            + configuration_errors(parser["general"], workflow, ruleset, runtime_manifest)
            + documented_minimum_errors(root, parser["general"]))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    try:
        errors = check_repository()
    except (OSError, ValueError, KeyError, TypeError, ConfigError, yaml.YAMLError, subprocess.CalledProcessError) as error:
        print(f"Repository consistency check failed: {error}", file=sys.stderr)
        return 1
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Repository documentation links, metadata, CI matrix and required checks agree.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
