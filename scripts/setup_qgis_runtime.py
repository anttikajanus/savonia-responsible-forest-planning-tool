"""Extract a pinned Windows QGIS test runtime into this checkout's .local folder."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.request
import uuid


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path(__file__).with_name("qgis-runtimes.json")
LOCAL_ROOT = ROOT / ".local" / "qgis-runtimes"


class SetupFailure(RuntimeError):
    """An actionable runtime setup failure."""


def contained(root, path):
    """Reject path escapes, including existing junctions/symlinks."""
    root, path = root.resolve(), path.resolve()
    if not path.is_relative_to(root) or path == root:
        raise SetupFailure(f"Path escapes workspace storage: {path}")
    return path


def leaf(value):
    """MSI table names must be plain Windows path components."""
    if not value or value in (".", "..") or re.search(r'[\\/:*?"<>|\x00-\x1f]', value):
        raise SetupFailure(f"Unsafe MSI path component: {value!r}")
    if value.endswith((".", " ")):
        raise SetupFailure(f"Unsafe MSI path component: {value!r}")
    return value


def load_runtime(version):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    selected = version or manifest["default_version"]
    for runtime in manifest["runtimes"]:
        if runtime["version"] == selected:
            leaf(runtime["version"])
            leaf(runtime["installer"])
            leaf(runtime["launcher"])
            if not re.fullmatch(r"[0-9a-f]{64}", runtime["sha256"]):
                raise SetupFailure("Invalid SHA-256 in runtime manifest")
            return manifest["base_url"], runtime
    raise SetupFailure(f"Unknown QGIS version {selected!r}; use --list to see pinned versions.")


def verify_hash(path, expected):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != expected:
        raise SetupFailure(f"QGIS installer checksum mismatch: {path}. "
                           "Remove the invalid file and retry with the pinned installer.")


def cached_installer(storage, base_url, runtime, source=None):
    cache = contained(storage, storage / "downloads" / runtime["sha256"])
    cache.mkdir(parents=True, exist_ok=True)
    destination = contained(cache, cache / runtime["installer"])
    if destination.exists():
        print(f"Verifying cached installer: {destination}", flush=True)
        verify_hash(destination, runtime["sha256"])
        return destination
    temporary = contained(cache, cache / f"{uuid.uuid4().hex}.part")
    try:
        if source:
            print(f"Caching existing installer: {source}", flush=True)
            shutil.copyfile(source, temporary)
        else:
            url = base_url.rstrip("/") + "/" + runtime["installer"]
            print(f"Downloading {url} (may exceed 1 GB)", flush=True)
            with urllib.request.urlopen(url, timeout=60) as response, temporary.open("wb") as output:
                shutil.copyfileobj(response, output, length=4 * 1024 * 1024)
        verify_hash(temporary, runtime["sha256"])
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def msi_layout(installer, target):
    """Read MSI metadata without invoking install actions or changing installer state."""
    try:
        import _msi  # Available in Windows CPython 3.10–3.12, including QGIS Python.
    except ImportError as error:
        raise SetupFailure("MSI extraction requires Windows CPython 3.10–3.12 with _msi. "
                           "Pass -Python pointing to an existing QGIS apps/Python312/python.exe.") from error
    def rows(query, columns):
        view = database.OpenView(query)
        view.Execute(None)
        try:
            while record := view.Fetch():
                yield tuple(record.GetString(i) for i in range(1, columns + 1))
        finally:
            view.Close()

    try:
        database = _msi.OpenDatabase(str(installer), 0)
        directories = {key: (parent, name) for key, parent, name in rows(
            "SELECT `Directory`, `Directory_Parent`, `DefaultDir` FROM `Directory`", 3)}
        components = dict(rows("SELECT `Component`, `Directory_` FROM `Component`", 2))
        files = list(rows("SELECT `File`, `Component_`, `FileName` FROM `File`", 3))
    except _msi.MSIError as error:
        raise SetupFailure(f"Could not read MSI tables from {installer}: {error}") from error
    return layout_paths(directories, components, files, target)


def layout_paths(directories, components, files, target):
    """Resolve and validate the complete destination map before extracting anything."""
    resolved = {}

    def directory(key, visiting):
        if key in visiting:
            raise SetupFailure(f"Cyclic MSI directory: {key}")
        if key not in resolved:
            parent, name = directories[key]
            if not parent:
                resolved[key] = target
            else:
                name = name.split(":")[0].split("|")[-1]
                base = directory(parent, visiting | {key})
                resolved[key] = base if name == "." else contained(target, base / leaf(name))
        return resolved[key]

    result = []
    destinations = set()
    for key, component, name in files:
        key = leaf(key)
        name = leaf(name.split("|")[-1])
        destination = contained(target, directory(components[component], set()) / name)
        # Windows paths are case insensitive even when tests run on another OS.
        normalized = str(destination).casefold()
        if normalized in destinations:
            raise SetupFailure(f"Duplicate MSI destination: {destination}")
        destinations.add(normalized)
        result.append((key, destination))
    if not result:
        raise SetupFailure("QGIS MSI contains no files")
    return result


def seven_zip_path(explicit=None):
    candidate = explicit or shutil.which("7z") or str(
        Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "7-Zip" / "7z.exe")
    if not Path(candidate).is_file():
        raise SetupFailure("7-Zip was not found. Supply -SevenZip with an existing 7z.exe path.")
    return str(Path(candidate).resolve())


def extract_runtime(installer, stage, runtime, seven_zip):
    target, flat = stage / "runtime", stage / "msi-files"
    target.mkdir()
    flat.mkdir()
    layout = msi_layout(installer, target)
    log = stage / "extract.log"
    print(f"Extracting QGIS {runtime['version']}; log: {log}", flush=True)
    with log.open("w", encoding="utf-8") as output:
        subprocess.run([seven_zip, "e", str(installer), "-y", f"-o{flat}", "-bso0", "-bsp0"],
                       stdout=output, stderr=subprocess.STDOUT, check=True)
    print(f"Reconstructing the MSI layout ({len(layout)} files)", flush=True)
    for key, destination in layout:
        source = contained(flat, flat / key)
        if not source.is_file():
            raise SetupFailure(f"MSI payload missing {key}; see {log}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        source.replace(destination)
    launchers = list(target.glob(f"*/bin/{runtime['launcher']}"))
    if len(launchers) != 1:
        raise SetupFailure(f"Expected one shipped {runtime['launcher']}; found {len(launchers)} in {target}")
    return launchers[0]


def verify_launcher(launcher, runtime, log):
    environment = os.environ.copy()
    environment.pop("PYTHONHOME", None)
    environment.pop("PYTHONPATH", None)
    environment["QT_QPA_PLATFORM"] = "offscreen"
    environment["PYTHONUTF8"] = "1"
    # No QgsApplication instance: importing Qgis does not open a QGIS user profile.
    code = ("from qgis.core import Qgis; print(Qgis.QGIS_VERSION); "
            f"assert Qgis.QGIS_VERSION_INT == {int(runtime['version_int'])}, 'Unexpected QGIS version'")
    with log.open("w", encoding="utf-8") as output:
        try:
            subprocess.run([str(launcher), "-c", code], env=environment, stdout=output,
                           stderr=subprocess.STDOUT, check=True, timeout=120)
        except (OSError, subprocess.SubprocessError) as error:
            raise SetupFailure(f"QGIS launcher/version verification failed: {launcher}; see {log}. "
                               "Use --rebuild to extract a fresh runtime.") from error


def setup_runtime(storage, base_url, runtime, source=None, seven_zip=None, rebuild=False):
    storage = contained(ROOT, storage)
    storage.mkdir(parents=True, exist_ok=True)
    destination = contained(storage, storage / "runtimes" / f"{runtime['version']}-{runtime['sha256'][:12]}")
    destination.mkdir(parents=True, exist_ok=True)
    state = contained(destination, destination / "runtime.json")
    if rebuild or not state.exists():
        seven_zip = seven_zip_path(seven_zip)
    installer = cached_installer(storage, base_url, runtime, source)
    if state.exists() and not rebuild:
        record = json.loads(state.read_text(encoding="utf-8"))
        if record["sha256"] != runtime["sha256"]:
            raise SetupFailure(f"Runtime state does not match the installer pin: {state}; use --rebuild.")
        launcher = contained(destination, destination / record["launcher"])
        verify_launcher(launcher, runtime, contained(destination, destination / "verify.log"))
        print("Reusing verified workspace runtime.", flush=True)
        return launcher
    stage = contained(destination, destination / f"extracted-{uuid.uuid4().hex[:12]}")
    stage.mkdir()
    try:
        launcher = extract_runtime(installer, stage, runtime, seven_zip)
        verify_launcher(launcher, runtime, stage / "verify.log")
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        raise SetupFailure(f"Runtime setup failed; diagnostics retained in {stage}: {error}") from error
    pending = contained(destination, destination / f"runtime-{uuid.uuid4().hex}.json.tmp")
    pending.write_text(json.dumps({"sha256": runtime["sha256"],
                                   "launcher": str(launcher.relative_to(destination))}, indent=2) + "\n",
                       encoding="utf-8")
    pending.replace(state)
    return launcher


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", help="Pinned baseline version (default: manifest default)")
    parser.add_argument("--list", action="store_true", help="List pinned versions without downloading")
    parser.add_argument("--installer", type=Path, help="Seed the download cache from an existing MSI")
    parser.add_argument("--seven-zip", help="Existing 7z.exe (default: PATH or Program Files)")
    parser.add_argument("--rebuild", action="store_true", help="Extract a fresh runtime, retaining earlier attempts")
    arguments = parser.parse_args(argv)
    if arguments.list:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        for runtime in manifest["runtimes"]:
            print(f"{runtime['version']}: {runtime['installer']} / {runtime['launcher']}")
        return 0
    try:
        if sys.platform != "win32":
            raise SetupFailure("Local QGIS runtime extraction is supported on Windows only.")
        base_url, runtime = load_runtime(arguments.version)
        if not (3, 10) <= sys.version_info[:2] <= (3, 12):
            raise SetupFailure("Use Windows CPython 3.10–3.12 for MSI extraction. "
                               "Pass -Python pointing to an existing QGIS apps/Python312/python.exe.")
        launcher = setup_runtime(LOCAL_ROOT, base_url, runtime, arguments.installer,
                                 arguments.seven_zip, arguments.rebuild)
    except (OSError, RuntimeError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f"QGIS runtime setup failed: {error}", file=sys.stderr)
        return 1
    quoted = str(launcher).replace("'", "''")
    print(f"QGIS Python launcher: {launcher}")
    print(f"Run checks: ./scripts/check.ps1 -QgisPython '{quoted}'")
    print(f"Or set for this session: $env:QGIS_PYTHON = '{quoted}'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
