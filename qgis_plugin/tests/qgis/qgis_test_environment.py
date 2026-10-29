"""One isolated, writable QGIS application for an integration-test process."""

import atexit
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import sys
import tempfile


_APPLICATION = None
_ROOT = None
_TEMPORARY = None


def check_writable_directory(directory):
    """Exercise real file/SQLite writes before debugging any provider failures."""
    directory = Path(directory)
    try:
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as folder:
            marker = Path(folder) / "writable.txt"
            marker.write_text("qgis-test", encoding="utf-8")
            if marker.read_text(encoding="utf-8") != "qgis-test":
                raise OSError("File round trip failed")
            with closing(sqlite3.connect(str(Path(folder) / "cache.sqlite"))) as database:
                database.execute("CREATE TABLE probe (value TEXT)")
                database.execute("INSERT INTO probe VALUES (?)", ("qgis-test",))
                database.commit()
                if database.execute("SELECT value FROM probe").fetchone() != ("qgis-test",):
                    raise OSError("SQLite round trip failed")
    except (OSError, sqlite3.Error) as error:
        raise RuntimeError(
            f"QGIS test directory is not writable: {directory}. "
            "Choose a writable temporary directory before running provider tests."
        ) from error


def environment_root():
    """Return the process-owned profile root, initializing QGIS when necessary."""
    qgis_application()
    return _ROOT


def qgis_application():
    """Initialize once, before test imports can read or write real QGIS settings."""
    global _APPLICATION, _ROOT, _TEMPORARY
    if _APPLICATION is not None:
        return _APPLICATION

    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    plugin_root = os.environ.get(
        "RESPONSIBLE_FOREST_PLANNING_TEST_PLUGIN_ROOT",
        str(Path(__file__).resolve().parents[2]),
    )
    sys.path.insert(0, plugin_root)
    parent = os.environ.get("RESPONSIBLE_FOREST_PLANNING_TEST_ENV_ROOT")
    if parent:
        _ROOT = Path(parent).resolve()
    else:
        _TEMPORARY = tempfile.TemporaryDirectory(prefix="savonia-qgis-tests-", ignore_cleanup_errors=True)
        atexit.register(_TEMPORARY.cleanup)
        _ROOT = Path(_TEMPORARY.name).resolve()
    for folder in ("settings", "system-settings", "profile", "auth", "cache"):
        check_writable_directory(_ROOT / folder)
    os.environ["QGIS_AUTH_DB_DIR_PATH"] = str(_ROOT / "auth")
    os.environ["QGIS_CUSTOM_CONFIG_PATH"] = str(_ROOT / "profile")

    # Both Qt scopes are redirected so default settings cannot fall back to the
    # user's credentials or preferences. These defaults last for this process.
    from qgis.PyQt.QtCore import QCoreApplication, QSettings
    from qgis.core import Qgis, QgsApplication, QgsProviderRegistry, QgsSettings

    if QgsApplication.instance() is not None:
        raise RuntimeError("Initialize the shared QGIS test environment before creating QgsApplication.")
    if not 40203 <= Qgis.QGIS_VERSION_INT < 50000:
        raise RuntimeError(f"QGIS 4.2.3 or newer 4.x is required; found {Qgis.QGIS_VERSION}.")
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(_ROOT / "settings"))
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.SystemScope, str(_ROOT / "system-settings"))
    QCoreApplication.setOrganizationName("SavoniaTests")
    QCoreApplication.setOrganizationDomain("savonia-tests.invalid")
    QCoreApplication.setApplicationName("QgisIntegration")
    # External QGIS 4.2 applications resolve their profile during initQgis()
    # using QGIS_CUSTOM_CONFIG_PATH. Set provider preferences after that step.
    application = QgsApplication([], True)
    application.initQgis()
    settings = QgsSettings()
    if (not Path(settings.fileName()).resolve().is_relative_to(_ROOT)
            or not Path(QgsApplication.qgisSettingsDirPath()).resolve().is_relative_to(_ROOT)):
        raise RuntimeError("QGIS test settings escaped the isolated profile; start a fresh test process.")
    settings.setValue("cache/directory", str(_ROOT / "cache"))
    settings.setValue("test-environment/preflight", "writable")
    settings.sync()
    saved = QSettings(settings.fileName(), QSettings.Format.IniFormat)
    saved.sync()
    if (not Path(settings.fileName()).is_file() or saved.status() != QSettings.Status.NoError
            or saved.value("test-environment/preflight") != "writable"):
        raise RuntimeError("QGIS test settings cannot be saved. Choose a writable test environment.")
    settings.remove("test-environment/preflight")
    settings.sync()
    providers = {name.lower() for name in QgsProviderRegistry.instance().providerList()}
    missing = {"memory", "ogr", "spatialite", "wfs", "oapif", "wms"} - providers
    if missing:
        raise RuntimeError("QGIS test providers are missing: " + ", ".join(sorted(missing)))
    _APPLICATION = application
    return _APPLICATION
