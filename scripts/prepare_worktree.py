"""Prepare a short ticket worktree and absolute worker context after Git write probes."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from uuid import uuid4

from dev_environment import default_qgis, managed_tools, runtime_inventory, shared_checkout


ROOT = Path(__file__).resolve().parents[1]


def git(root, *arguments):
    return subprocess.run(["git", *arguments], cwd=root, capture_output=True,
                          text=True, check=True, timeout=60).stdout.strip()


def metadata_access(root):
    """Probe actual directories with disposable files, leaving refs/index untouched."""
    common = Path(git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve()
    index = Path(git(root, "rev-parse", "--path-format=absolute", "--git-path", "index")).resolve()
    targets = [common, common / "refs/heads", common / "worktrees", index.parent]
    probes = []
    for target in dict.fromkeys(targets):
        # Probe the closest existing parent when Git has not created a directory.
        directory = target
        while not directory.exists():
            directory = directory.parent
        probe = directory / ("agent-write-probe-" + uuid4().hex)
        operation = "create probe file"
        try:
            descriptor = os.open(probe, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(descriptor)
            operation = "delete probe file"
            probe.unlink()
            probes.append({"path": str(directory), "writable": True})
        except OSError as error:
            probes.append({"path": str(directory), "writable": False, "operation": operation,
                           "error": str(error)})
    return {"shared_checkout": str(shared_checkout(root)), "git_common_dir": str(common),
            "git_metadata_writable": all(item["writable"] for item in probes), "probes": probes}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", help="Short ticket name, 1-16 lowercase letters/digits/hyphens")
    parser.add_argument("--spec", type=Path, help="Existing spec; relative paths start at the primary checkout")
    parser.add_argument("--base", default="HEAD", help="Base commit or integration branch")
    parser.add_argument("--branch", help="New branch (default: ticket/<name>)")
    parser.add_argument("--qgis-version", help="Require one available pinned QGIS baseline")
    parser.add_argument("--probe", action="store_true", help="Only check Git metadata access in this process")
    parser.add_argument("--repository", type=Path, default=ROOT, help="Checkout whose metadata is being prepared/probed")
    arguments = parser.parse_args(argv)
    root = arguments.repository.resolve()
    try:
        if arguments.probe:
            access = metadata_access(root)
            print(json.dumps(access, indent=2))
            if not access["git_metadata_writable"]:
                print("Git metadata is not writable in this context. An authorized owner must perform Git mutations.",
                      file=sys.stderr)
            return int(not access["git_metadata_writable"])
        if not arguments.name or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,15}", arguments.name):
            raise ValueError("Use --name with 1-16 lowercase letters, digits or hyphens, starting with a letter or digit.")
        shared = shared_checkout(root)
        if arguments.spec is None:
            raise ValueError("Supply --spec with an existing working specification.")
        spec = (shared / arguments.spec).resolve()
        if not spec.is_file():
            raise ValueError(f"Working spec is missing: {spec}")
        worktree_root = (shared / ".local/wt").resolve()
        worktree = (worktree_root / arguments.name).resolve()
        if not worktree_root.is_relative_to(shared) or not worktree.is_relative_to(worktree_root) or worktree.exists():
            raise ValueError(f"Worktree destination must be new and inside {worktree_root}: {worktree}")
        context_file = (shared / ".local/task-contexts" / (arguments.name + ".json")).resolve()
        if not context_file.is_relative_to(shared):
            raise ValueError(f"Task context must remain inside the primary checkout: {context_file}")
        if context_file.exists():
            raise ValueError(f"Task context already exists; use a new short name: {context_file}")
        branch = arguments.branch or "ticket/" + arguments.name
        git(root, "check-ref-format", "--branch", branch)
        revision = git(root, "rev-parse", "--verify", "--end-of-options", arguments.base + "^{commit}")
        _manifest, inventory = runtime_inventory(root)
        if arguments.qgis_version and not inventory.get(arguments.qgis_version, {}).get("launcher_path"):
            raise ValueError(f"QGIS {arguments.qgis_version} is unavailable. Run setup-dev-environment.ps1 first.")
        access = metadata_access(root)
        if not access["git_metadata_writable"]:
            print(json.dumps(access, indent=2))
            raise ValueError("Git metadata is not writable here. Have an authorized owner run this preparation command; "
                             "workers can edit the prepared files and report commits they cannot perform.")
        config = managed_tools(root)
        launcher = inventory[arguments.qgis_version]["launcher_path"] if arguments.qgis_version else default_qgis(root)
        launcher = str(Path(launcher).resolve()) if launcher and Path(launcher).is_file() else None
        context = {"schema_version": 1, "worktree": str(worktree), "branch": branch,
                   "base_revision": revision, "spec": str(spec), "context_file": str(context_file),
                   "git_common_dir": access["git_common_dir"], "preparer_git_metadata_writable": True,
                   "shared_checkout": str(shared), "python": config.get("python") or sys.executable,
                   "tooling_path": config.get("tooling_path"), "qgis_python": launcher,
                   "runtimes": inventory,
                   "worker_probe_command": [sys.executable, str(Path(__file__).resolve()), "--probe",
                                            "--repository", str(worktree)]}
        context["check_command"] = ["powershell", "-NoProfile", "-File", str(worktree / "scripts/check.ps1"),
                                    "-Python", context["python"]]
        if launcher:
            context["check_command"] += ["-QgisPython", launcher]
        if config.get("tooling_path"):
            context["check_command"] += ["-ToolsPath", config["tooling_path"]]
        worktree_root.mkdir(parents=True, exist_ok=True)
        context_file.parent.mkdir(parents=True, exist_ok=True)
        git(root, "worktree", "add", "-b", branch, "--", str(worktree), revision)
        with context_file.open("x", encoding="utf-8") as output:
            output.write(json.dumps(context, indent=2) + "\n")
        print(json.dumps(context, indent=2))
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        detail = error.stderr.strip() if isinstance(error, subprocess.CalledProcessError) and error.stderr else str(error)
        print(f"Worktree preparation failed: {detail}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
