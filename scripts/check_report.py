"""Persist the actual coverage of a local check run, including interrupted stages."""

from datetime import datetime, timezone
import json
import re
import subprocess


CHECK_GROUPS = ("tooling", "unit", "lint", "qgis")


def source_state(root):
    """Record Git identity without requiring Git for otherwise independent checks."""
    state = {"root": str(root), "revision": None, "dirty": None}
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
                              text=True, check=True, timeout=10)
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True,
                               text=True, check=True, timeout=10)
        state.update(revision=head.stdout.strip(), dirty=bool(dirty.stdout.strip()))
    except (OSError, subprocess.SubprocessError) as error:
        state["error"] = str(error)
    return state


def test_counts(log):
    """Use unittest's final report; absence of a report is unknown, never zero."""
    output = log.read_text(encoding="utf-8", errors="replace")
    reports = list(re.finditer(r"^Ran (\d+) tests? in .+$", output, re.MULTILINE))
    if not reports:
        return None
    tail = output[reports[-1].end():]
    counts = {"run": int(reports[-1][1]), "failures": 0, "errors": 0, "skipped": 0,
              "expected_failures": 0, "unexpected_successes": 0}
    for key, field in (("failures", "failures"), ("errors", "errors"), ("skipped", "skipped"),
                       ("expected failures", "expected_failures"),
                       ("unexpected successes", "unexpected_successes")):
        match = re.search(rf"(?:\(|,)\s*{re.escape(key)}=(\d+)(?=[,)])", tail)
        if match:
            counts[field] = int(match[1])
    # A native crash after unittest's count cannot establish a successful stage.
    return counts


def record_stage(logs, name, status, elapsed, exit_code=None):
    log = logs / (name + ".log")
    payload = {"status": status, "elapsed_seconds": round(elapsed, 3),
               "exit_code": exit_code, "log": str(log), "tests": test_counts(log)}
    (logs / (name + ".result.json")).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def stage_plan(arguments):
    selected = set(arguments.checks)
    return {
        "preflight-git": "tooling" in selected,
        "preflight-tooling": "tooling" in selected,
        "preflight-qgis": bool({"lint", "qgis"} & selected),
        "preflight-lint": "lint" in selected,
        **{name: name in selected for name in CHECK_GROUPS},
        "package": arguments.package,
        "unit-package": arguments.package and "unit" in selected,
        "qgis-package": arguments.package and "qgis" in selected,
    }


def write_summary(arguments, logs, source, status, error=None):
    stages = {}
    for name, selected in stage_plan(arguments).items():
        result = logs / (name + ".result.json")
        stages[name] = json.loads(result.read_text(encoding="utf-8")) if result.exists() else {
            "status": "not_run" if selected else "not_selected", "tests": None,
        }
    failed_stage = getattr(error, "stage", None)
    if failed_stage in stages and stages[failed_stage]["status"] == "not_run":
        stages[failed_stage].update(status="failed", error=str(error))
    payload = {
        "schema_version": 1, "status": status, "source": source,
        "source_after": source_state(source["root"]),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "selected_checks": [name for name in CHECK_GROUPS if name in arguments.checks],
        "not_selected_checks": [name for name in CHECK_GROUPS if name not in arguments.checks],
        "package_requested": arguments.package, "qgis_pattern": arguments.qgis_pattern,
        "interpreters": {"plain_python": arguments.plain_python,
                         "qgis_python": arguments.qgis_python,
                         "tooling_path": arguments.tools_path},
        "stages": stages, "error": str(error) if error else None,
    }
    destination = logs / "summary.json"
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(destination)
    return destination
