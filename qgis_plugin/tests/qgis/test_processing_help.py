"""Real Processing help callbacks use the installed package and QGIS language."""

import importlib
import importlib.util
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from qgis.PyQt.QtCore import QUrl
from qgis.core import Qgis, QgsApplication, QgsMessageLog, QgsSettings

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
APP = QgsApplication.instance()
if APP is None:
    APP = QgsApplication([], False)
    APP.initQgis()


class ProcessingHelpTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix="Metsä Processing help ")
        self.addCleanup(self.folder.cleanup)
        root = Path(self.folder.name)
        source = Path(os.environ.get("SAVONIA_TEST_PLUGIN_ROOT", str(Path(__file__).resolve().parents[2])))
        package = "savonia_responsible_forest_planning_tool"
        staging = root / "staging" / package
        shutil.copytree(source / package, staging, ignore=shutil.ignore_patterns("__pycache__"))
        docs = staging / "docs" / "help"
        docs.mkdir(parents=True, exist_ok=True)
        for language in ("fi", "en"):
            manual = docs / f"manual_{language}.html"
            if not manual.exists():
                text = (source.parent / "docs" / "help" / manual.name).read_text(encoding="utf-8")
                text = text.replace("../../qgis_plugin/" + package + "/", "../../")
                manual.write_text(text, encoding="utf-8")
        archive = shutil.make_archive(str(root / "plugin"), "zip", root / "staging")
        extracted = root / "extracted plugin"
        shutil.unpack_archive(archive, extracted)
        self.package_root = extracted / package
        self.alias = "savonia_processing_help_fixture"
        spec = importlib.util.spec_from_file_location(self.alias, self.package_root / "__init__.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[self.alias] = module
        spec.loader.exec_module(module)
        self.provider = importlib.import_module(self.alias + ".processing.provider")
        self.i18n = importlib.import_module(self.alias + ".i18n")
        self.addCleanup(self.remove_modules)
        settings = QgsSettings()
        key = "savonia_responsible_forest_planning_tool/language"
        existed, previous = settings.contains(key), settings.value(key)
        self.addCleanup(lambda: settings.setValue(key, previous) if existed else settings.remove(key))
        self.qgis_locale = self.enterContext(patch.object(QgsApplication, "locale", return_value="en_GB"))

    def remove_modules(self):
        for name in tuple(sys.modules):
            if name == self.alias or name.startswith(self.alias + "."):
                del sys.modules[name]

    def test_help_url_follows_qgis_in_extracted_zip_despite_legacy_plugin_override(self):
        for language in ("fi", "en"):
            with self.subTest(language=language):
                self.qgis_locale.return_value = language
                QgsSettings().setValue("savonia_responsible_forest_planning_tool/language",
                                       "en" if language == "fi" else "fi")
                algorithm = self.provider.ResponsibleForestPlanningInputsAlgorithm()
                url = algorithm.helpUrl()
                parsed = QUrl(url)
                self.assertTrue(parsed.isLocalFile())
                self.assertEqual(parsed.fragment(), "processing")
                self.assertEqual(Path(parsed.toLocalFile()), (self.package_root / "docs" / "help" / f"manual_{language}.html").resolve())
                self.assertIn("Mets%C3%A4%20Processing%20help%20", url)
                self.assertIn('id="processing"', Path(parsed.toLocalFile()).read_text(encoding="utf-8"))

    def test_missing_manual_reports_selected_language_and_diagnostics_without_callback_exception(self):
        for language, correction in (("fi", "Asenna"), ("en", "Reinstall")):
            with self.subTest(language=language):
                self.qgis_locale.return_value = language
                (self.package_root / "docs" / "help" / f"manual_{language}.html").unlink()
                with self.assertLogs("savonia_responsible_forest_planning_tool", level="ERROR") as logs, \
                        patch.object(QgsMessageLog, "logMessage") as notification:
                    url = self.provider.ResponsibleForestPlanningInputsAlgorithm().helpUrl()
                self.assertEqual(url, "")
                self.assertIn(correction, notification.call_args.args[0])
                self.assertEqual(notification.call_args.args[2], Qgis.MessageLevel.Warning)
                self.assertTrue(notification.call_args.kwargs["notifyUser"])
                self.assertIn("unreadable", logs.output[0])
                self.assertIn(f"manual_{language}.html", logs.output[0])
                self.assertTrue(logs.records[0].exc_info)

    def test_short_help_explains_parameters_outputs_and_limits_in_both_languages(self):
        for language, limit in (("fi", "oikeudellisia"), ("en", "legal")):
            with self.subTest(language=language):
                self.qgis_locale.return_value = language
                help_text = self.provider.ResponsibleForestPlanningInputsAlgorithm().shortHelpString()
                for parameter in ("AOI", "SELECTED_ONLY", "STANDS", "GRIDCELLS", "HABITATS", "PROTECTED",
                                  "PROTECTED_PRIVATE", "PROTECTED_WILDERNESS", "PROGRAMME", "GROUNDWATER",
                                  "OUTPUT_FOLDER", "OUTPUT_NAME", "RESULT", "EXCEL"):
                    self.assertIn(parameter, help_text)
                self.assertIn("GeoPackage", help_text)
                self.assertIn(limit, help_text)
                self.assertTrue(help_text.startswith(self.i18n.tr(language, "prototype_notice")))


if __name__ == "__main__":
    unittest.main()
