"""Workspace runtime caching, extraction safety and completion guarantees."""

from contextlib import redirect_stderr, redirect_stdout
import hashlib
from io import BytesIO, StringIO
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import setup_qgis_runtime as setup


class RuntimeSetupTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.addCleanup(patch.stopall)
        patch.object(setup, "ROOT", self.root).start()
        self.storage = self.root / ".local" / "qgis-runtimes"
        self.payload = b"controlled MSI payload"
        self.runtime = {"version": "3.44.0", "version_int": 34400,
                        "installer": "QGIS-test.msi", "launcher": "python-qgis-ltr.bat",
                        "sha256": hashlib.sha256(self.payload).hexdigest()}
        self.source = self.root / "seed.msi"
        self.source.write_bytes(self.payload)
        self.output = StringIO()
        self.redirect = redirect_stdout(self.output)
        self.redirect.__enter__()
        self.addCleanup(self.redirect.__exit__, None, None, None)

    def test_seeded_cache_is_verified_and_reused_without_network(self):
        with patch.object(setup.urllib.request, "urlopen") as download:
            first = setup.cached_installer(self.storage, "https://example.test", self.runtime, self.source)
            self.source.unlink()
            second = setup.cached_installer(self.storage, "https://example.test", self.runtime)
        self.assertEqual(first, second)
        self.assertEqual(first.read_bytes(), self.payload)
        download.assert_not_called()
        first.write_bytes(b"corrupted")
        with self.assertRaisesRegex(setup.SetupFailure, "checksum mismatch"):
            setup.cached_installer(self.storage, "https://example.test", self.runtime)

    def test_download_only_promotes_verified_complete_content(self):
        for content in (b"truncated", self.payload):
            with self.subTest(content=content), patch.object(
                    setup.urllib.request, "urlopen", return_value=BytesIO(content)):
                if content != self.payload:
                    with self.assertRaisesRegex(setup.SetupFailure, "checksum mismatch"):
                        setup.cached_installer(self.storage, "https://example.test", self.runtime)
                    self.assertEqual(list(self.storage.rglob("*.msi")), [])
                else:
                    path = setup.cached_installer(self.storage, "https://example.test", self.runtime)
                    self.assertEqual(path.read_bytes(), content)
                self.assertEqual(list(self.storage.rglob("*.part")), [])

    def test_network_failure_does_not_leave_a_cache_hit(self):
        with patch.object(setup.urllib.request, "urlopen", side_effect=OSError("connection lost")):
            with self.assertRaisesRegex(OSError, "connection lost"):
                setup.cached_installer(self.storage, "https://example.test", self.runtime)
        self.assertEqual(list(self.storage.rglob("*.msi")), [])
        self.assertEqual(list(self.storage.rglob("*.part")), [])

    def test_msi_layout_uses_long_target_names_and_component_directories(self):
        target = self.root / "runtime"
        paths = setup.layout_paths(
            {"root": ("", "SourceDir"), "qgis": ("root", "QGIS34~1|QGIS 3.44.0:source"),
             "bin": ("qgis", "bin"), "same": ("bin", ".")},
            {"component": "same"}, [("file_key", "component", "PYTHON~1.BAT|python-qgis-ltr.bat")], target)
        self.assertEqual(paths, [("file_key", target / "QGIS 3.44.0/bin/python-qgis-ltr.bat")])

    def test_unsafe_msi_paths_and_cycles_are_rejected_before_extraction(self):
        for name in ("..", "../escape", "C:\\outside", "file:stream", "trailing.", "trailing "):
            with self.subTest(name=name), self.assertRaises(setup.SetupFailure):
                setup.layout_paths({"root": ("", "SourceDir")}, {"c": "root"},
                                   [("key", "c", name)], self.root / "runtime")
        with self.assertRaisesRegex(setup.SetupFailure, "Cyclic"):
            setup.layout_paths({"a": ("b", "a"), "b": ("a", "b")}, {"c": "a"},
                               [("key", "c", "file")], self.root / "runtime")
        with self.assertRaisesRegex(setup.SetupFailure, "Duplicate"):
            setup.layout_paths({"root": ("", "SourceDir")}, {"c": "root"},
                               [("a", "c", "file"), ("b", "c", "FILE")], self.root / "runtime")

    def fake_extract(self, _installer, stage, runtime, _seven_zip):
        launcher = stage / "runtime" / "QGIS test" / "bin" / runtime["launcher"]
        launcher.parent.mkdir(parents=True)
        launcher.touch()
        return launcher

    def test_completed_runtime_rechecks_version_and_reuses_shipped_launcher(self):
        with patch.object(setup, "seven_zip_path", return_value="7z.exe"), patch.object(
                setup, "extract_runtime", side_effect=self.fake_extract) as extract, patch.object(
                setup, "verify_launcher") as verify:
            launcher = setup.setup_runtime(self.storage, "", self.runtime, self.source)
            self.assertEqual(launcher.name, "python-qgis-ltr.bat")
            reused = setup.setup_runtime(self.storage, "", self.runtime)
            self.assertEqual(reused, launcher)
            self.assertEqual(extract.call_count, 1)
            self.assertEqual(verify.call_count, 2)
            rebuilt = setup.setup_runtime(self.storage, "", self.runtime, rebuild=True)
            self.assertNotEqual(rebuilt, launcher)
            self.assertTrue(launcher.exists(), "Rebuild must preserve the previous extraction")

    def test_wrong_version_does_not_publish_runtime_state(self):
        with patch.object(setup, "seven_zip_path", return_value="7z.exe"), patch.object(
                setup, "extract_runtime", side_effect=self.fake_extract), patch.object(
                setup, "verify_launcher", side_effect=setup.SetupFailure("wrong version")):
            with self.assertRaisesRegex(setup.SetupFailure, "wrong version"):
                setup.setup_runtime(self.storage, "", self.runtime, self.source)
        self.assertEqual(list(self.storage.rglob("runtime.json")), [])
        self.assertEqual(len(list(self.storage.rglob("extracted-*"))), 1)

    def test_extraction_failure_retains_diagnostics_without_completion_marker(self):
        def fail(_installer, stage, _runtime, _seven_zip):
            (stage / "extract.log").write_text("controlled extraction failure")
            raise subprocess.CalledProcessError(2, "7z")

        with patch.object(setup, "seven_zip_path", return_value="7z.exe"), patch.object(
                setup, "extract_runtime", side_effect=fail):
            with self.assertRaisesRegex(setup.SetupFailure, "diagnostics retained"):
                setup.setup_runtime(self.storage, "", self.runtime, self.source)
        self.assertEqual(list(self.storage.rglob("runtime.json")), [])
        self.assertEqual(next(self.storage.rglob("extract.log")).read_text(), "controlled extraction failure")

    def test_runtime_state_cannot_select_launcher_outside_local_storage(self):
        with patch.object(setup, "seven_zip_path", return_value="7z.exe"), patch.object(
                setup, "extract_runtime", side_effect=self.fake_extract), patch.object(setup, "verify_launcher"):
            setup.setup_runtime(self.storage, "", self.runtime, self.source)
        state = next(self.storage.rglob("runtime.json"))
        state.write_text(json.dumps({"sha256": self.runtime["sha256"], "launcher": str(self.source)}))
        with self.assertRaisesRegex(setup.SetupFailure, "escapes workspace"):
            setup.setup_runtime(self.storage, "", self.runtime)

    def test_storage_outside_checkout_is_rejected(self):
        with self.assertRaisesRegex(setup.SetupFailure, "escapes workspace"):
            setup.setup_runtime(self.root.parent / "outside", "", self.runtime)

    def test_missing_extractor_stops_before_downloading(self):
        with patch.object(setup, "seven_zip_path", side_effect=setup.SetupFailure("7-Zip missing")), patch.object(
                setup, "cached_installer") as cache:
            with self.assertRaisesRegex(setup.SetupFailure, "7-Zip missing"):
                setup.setup_runtime(self.storage, "", self.runtime)
        cache.assert_not_called()

    def test_unsupported_bootstrap_python_stops_before_downloading(self):
        with patch.object(setup.sys, "platform", "win32"), patch.object(
                setup.sys, "version_info", (3, 13, 0)), redirect_stderr(StringIO()), patch.object(
                setup, "cached_installer") as cache:
            self.assertEqual(setup.main([]), 1)
        cache.assert_not_called()

    def test_launcher_failure_reports_log_and_uses_an_isolated_import_environment(self):
        launcher = self.root / "python-qgis.bat"
        log = self.root / "verify.log"
        with patch.dict(setup.os.environ, {"PYTHONHOME": "wrong", "PYTHONPATH": "wrong"}), patch.object(
                setup.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "launcher")) as run:
            with self.assertRaisesRegex(setup.SetupFailure, "launcher/version verification failed"):
                setup.verify_launcher(launcher, self.runtime, log)
        self.assertTrue(log.exists())
        environment = run.call_args.kwargs["env"]
        self.assertNotIn("PYTHONHOME", environment)
        self.assertNotIn("PYTHONPATH", environment)
        self.assertIn("34400", run.call_args.args[0][-1])

    def test_unknown_version_fails_before_any_download(self):
        error = StringIO()
        with patch.object(setup.sys, "platform", "win32"), redirect_stderr(error), patch.object(
                setup, "cached_installer") as cache:
            self.assertEqual(setup.main(["--version", "unknown"]), 1)
        self.assertIn("--list", error.getvalue())
        cache.assert_not_called()


if __name__ == "__main__":
    unittest.main()
