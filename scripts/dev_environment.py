"""Discover shared local tooling and QGIS runtimes from any linked worktree."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def shared_checkout(root):
    """Git lists the primary checkout first, including from linked worktrees."""
    try:
        result = subprocess.run(["git", "worktree", "list", "--porcelain"], cwd=root,
                                capture_output=True, text=True, check=True, timeout=10)
        first = result.stdout.splitlines()[0]
        if first.startswith("worktree "):
            return Path(first.removeprefix("worktree ")).resolve()
    except (OSError, subprocess.SubprocessError, IndexError):
        pass
    return Path(root).resolve()


def runtime_inventory(root):
    manifest = json.loads((Path(root) / "scripts/qgis-runtimes.json").read_text(encoding="utf-8"))
    shared = shared_checkout(root)
    inventory = {}
    for item in manifest["runtimes"]:
        storage = shared / ".local/qgis-runtimes/runtimes" / (item["version"] + "-" + item["sha256"][:12])
        state = storage / "runtime.json"
        launcher = None
        if state.is_file():
            try:
                record = json.loads(state.read_text(encoding="utf-8"))
                candidate = (storage / record["launcher"]).resolve()
                if record["sha256"] == item["sha256"] and candidate.is_relative_to(storage.resolve()) and candidate.is_file():
                    launcher = candidate
            except (OSError, ValueError, KeyError):
                pass
        installed = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / ("QGIS " + item["version"]) / "bin" / item["launcher"]
        if launcher is None and installed.is_file():
            launcher = installed.resolve()
        inventory[item["version"]] = {**item, "launcher_path": str(launcher) if launcher else None,
                                      "status": "available" if launcher else "missing"}
    return manifest, inventory


def managed_tools(root):
    directory = shared_checkout(root) / ".local/dev-environment"
    state = directory / "environment.json"
    if not state.is_file():
        return {}
    try:
        config = json.loads(state.read_text(encoding="utf-8"))
        python = Path(config["python"]).resolve()
        site = Path(config["tooling_path"]).resolve()
        if (config.get("tooling_ready") and python.is_relative_to(directory) and site.is_relative_to(directory)
                and python.is_file() and site.is_dir()):
            return config
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return {}


def default_qgis(root):
    if os.environ.get("QGIS_PYTHON"):
        return os.environ["QGIS_PYTHON"]
    manifest, inventory = runtime_inventory(root)
    configured = managed_tools(root).get("default_version", manifest["default_version"])
    preferred = inventory.get(configured, {})
    if preferred.get("launcher_path"):
        return preferred["launcher_path"]
    for item in inventory.values():
        if item["launcher_path"]:
            return item["launcher_path"]
    default = manifest["default_version"]
    return str(Path(os.environ.get("ProgramFiles", "C:/Program Files")) / ("QGIS " + default) /
               "bin" / inventory[default]["launcher"])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--python")
    parser.add_argument("--qgis-python")
    parser.add_argument("--tools-path")
    arguments = parser.parse_args(argv)
    try:
        config = managed_tools(arguments.repository)
        print(json.dumps({
            "python": arguments.python or config.get("python") or sys.executable,
            "qgis_python": arguments.qgis_python or default_qgis(arguments.repository),
            "tools_path": arguments.tools_path or config.get("tooling_path"),
            "shared_root": str(shared_checkout(arguments.repository)),
        }))
        return 0
    except (OSError, ValueError, KeyError) as error:
        print(f"Development path discovery failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
