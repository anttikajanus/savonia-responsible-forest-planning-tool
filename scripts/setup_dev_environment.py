"""Prepare isolated development dependencies and pinned shared QGIS runtimes."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from uuid import uuid4

from dev_environment import runtime_inventory, shared_checkout
import setup_qgis_runtime as runtime


ROOT = Path(__file__).resolve().parents[1]


def run_stage(command, root, log):
    environment = dict(os.environ, PYTHONNOUSERSITE="1", PYTHONUTF8="1", QT_QPA_PLATFORM="offscreen",
                       PIP_DISABLE_PIP_VERSION_CHECK="1", PIP_CACHE_DIR=str(log.parent.parent / "pip-cache"))
    for name in ("PYTHONHOME", "PYTHONPATH"):
        environment.pop(name, None)
    with log.open("a", encoding="utf-8") as output:
        subprocess.run([str(value) for value in command], cwd=root, stdout=output,
                       env=environment, stderr=subprocess.STDOUT, check=True, timeout=1200)


def save_config(directory, config):
    temporary = directory / ("environment-" + uuid4().hex + ".tmp")
    temporary.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    temporary.replace(directory / "environment.json")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="append", help="Prepare a pinned baseline (repeatable; default: all)")
    parser.add_argument("--seven-zip", help="Existing 7z.exe for missing runtime extraction")
    parser.add_argument("--status", action="store_true", help="Show discovered paths without changing files")
    arguments = parser.parse_args(argv)
    manifest, inventory = runtime_inventory(ROOT)
    selected = arguments.version or list(inventory)
    if set(selected) - set(inventory):
        parser.error("Unknown baseline: " + ", ".join(sorted(set(selected) - set(inventory))))
    if arguments.status:
        print(json.dumps({"shared_checkout": str(shared_checkout(ROOT)), "runtimes": inventory}, indent=2))
        return 0

    shared = shared_checkout(ROOT)
    directory = shared / ".local/dev-environment"
    directory.mkdir(parents=True, exist_ok=True)
    logs = directory / "logs"
    logs.mkdir(exist_ok=True)
    log = logs / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid4().hex[:8] + ".log")
    environment = directory / "venv"
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    site = environment / ("Lib/site-packages" if os.name == "nt" else
                          f"lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages")
    config = {"schema_version": 1, "status": "failed", "python": str(python),
              "tooling_path": str(site), "tooling_ready": False, "log": str(log),
              "default_version": manifest["default_version"] if manifest["default_version"] in selected else selected[0],
              "runtimes": {version: {**item, "status": "not_run" if version in selected else "not_selected"}
                           for version, item in inventory.items()}}
    # Invalidate stale readiness before installation or a runtime probe can fail.
    save_config(directory, config)
    try:
        if not python.is_file():
            run_stage([sys.executable, "-m", "venv", str(environment)], ROOT, log)
        shutil.copyfile(Path(__file__).with_name("development_sitecustomize.py"), site / "sitecustomize.py")
        run_stage([python, "-c", "import ssl; print(ssl.OPENSSL_VERSION)"], ROOT, log)
        run_stage([python, "-m", "pip", "install", "--upgrade", "-r", ROOT / "requirements-dev.txt"], ROOT, log)
        run_stage([python, ROOT / "scripts/check_tooling_environment.py"], ROOT, log)
        config["tooling_ready"] = True
    except (OSError, subprocess.SubprocessError) as error:
        config["error"] = str(error)
        save_config(directory, config)
        print(f"Tooling preparation failed: {error}. Log: {log}", file=sys.stderr)
        return 1

    failed = False
    for version in selected:
        item = inventory[version]
        try:
            # Cached setup verifies the actual launcher/version again; new setup
            # retains the existing checksum, extraction and diagnostic policy.
            if item.get("launcher_path"):
                launcher = Path(item["launcher_path"])
                runtime.verify_launcher(launcher, item, logs / ("qgis-" + version + ".log"))
            else:
                launcher = runtime.setup_runtime(shared / ".local/qgis-runtimes", manifest["base_url"],
                                                 item, seven_zip=arguments.seven_zip)
            run_stage([launcher, ROOT / "scripts/run_dev_tool.py", "--tools-path", site,
                       "--script", ROOT / "scripts/check_lint_environment.py", "--qgis-python", launcher], ROOT, log)
            config["runtimes"][version].update(status="ready", launcher_path=str(launcher.resolve()))
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
            failed = True
            config["runtimes"][version].update(status="failed", error=str(error))
    config["status"] = "failed" if failed else "ready"
    save_config(directory, config)
    for version, item in config["runtimes"].items():
        print(f"QGIS {version}: {item['status']}; launcher: {item.get('launcher_path') or 'unavailable'}")
        if item.get("error"):
            print(item["error"], file=sys.stderr)
    print(f"Plain Python: {python}\nManaged tooling: {site}\nEnvironment: {directory / 'environment.json'}\nLog: {log}")
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
