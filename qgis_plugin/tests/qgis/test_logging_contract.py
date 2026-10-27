"""Owned logging lifecycle, separate payloads and failure isolation."""

import json
import logging
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.environ.get(
    "RESPONSIBLE_FOREST_PLANNING_TEST_PLUGIN_ROOT",
    os.environ.get("SAVONIA_TEST_PLUGIN_ROOT", str(Path(__file__).resolve().parents[2])),
))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qgis.core import Qgis, QgsApplication, QgsMessageLog, QgsProcessingException, QgsProcessingFeedback

APP = QgsApplication.instance()
if APP is None:
    APP = QgsApplication([], False)
    APP.initQgis()

from savonia_responsible_forest_planning_tool import app_logging
from savonia_responsible_forest_planning_tool.analysis import workflow
from workflow_fixture import WorkflowFixtureMixin


class LoggingContractTests(WorkflowFixtureMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.settings = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.settings.cleanup)
        self.enterContext(patch.object(QgsApplication, "qgisSettingsDirPath", return_value=self.settings.name))
        self.panel = self.enterContext(patch.object(QgsMessageLog, "logMessage"))
        self.addCleanup(app_logging.shutdown_logging)

    def test_reload_unload_closes_only_owned_handlers_and_keeps_root_unchanged(self):
        root = logging.getLogger()
        original_root = (list(root.handlers), root.level)
        technical = logging.getLogger(app_logging.LOGGER_NAME)
        external = logging.NullHandler()
        technical.addHandler(external)
        self.addCleanup(technical.removeHandler, external)
        folder = Path(app_logging.configure_logging())
        first = [handler for handler in technical.handlers if isinstance(handler, logging.FileHandler)]
        app_logging.configure_logging()
        self.assertTrue(all(handler.stream is None for handler in first))
        owned = [handler for handler in technical.handlers if handler is not external]
        self.assertEqual(len(owned), 2)
        file_handler, = [handler for handler in owned if isinstance(handler, logging.FileHandler)]
        self.assertEqual((file_handler.maxBytes, file_handler.backupCount), (2 * 1024 * 1024, 3))
        technical.info("one event after reload")
        app_logging.shutdown_logging()
        app_logging.shutdown_logging()
        self.assertEqual(technical.handlers, [external])
        self.assertIsNone(file_handler.stream)
        self.assertEqual((list(root.handlers), root.level), original_root)
        self.assertEqual((folder / "technical.log").read_text(encoding="utf-8").count("one event after reload"), 1)

    def test_workflow_events_are_aggregate_json_and_tracebacks_stay_in_technical_file(self):
        folder = Path(app_logging.configure_logging())
        with self.scenario([]) as (_, layers, aoi):
            self.run_algorithm(layers, aoi, "fi", "logged-success")
        with self.assertRaises(QgsProcessingException):
            workflow.run_workflow({"language": "en", "output_folder": "private-path-marker"})
        feedback = QgsProcessingFeedback()
        feedback.cancel()
        with self.assertRaises(QgsProcessingException):
            workflow.run_workflow({"language": "fi"}, feedback)
        app_logging.shutdown_logging()
        events = [json.loads(line) for line in (folder / "business-actions.jsonl").read_text(encoding="utf-8").splitlines()]
        outcomes = [event for event in events if event["event"] != "analysis_run_started"]
        self.assertEqual([event["event"] for event in outcomes],
                         ["analysis_run_completed", "analysis_run_failed", "analysis_run_cancelled"])
        allowed = {"timestamp_utc", "event", "run_id", "entry_point", "selected_features_only",
                   "configured_source_count", "result_feature_count", "stage", "error_type"}
        for event in events:
            self.assertLessEqual(set(event), allowed)
            self.assertRegex(event["timestamp_utc"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$")
            self.assertNotIn("private-path-marker", json.dumps(event))
        for outcome in outcomes:
            self.assertEqual(sum(event["event"] == "analysis_run_started" and event["run_id"] == outcome["run_id"]
                                 for event in events), 1)
        technical = (folder / "technical.log").read_text(encoding="utf-8")
        self.assertIn("Traceback", technical)
        self.assertIn("stage=input_validation", technical)
        self.assertTrue(all("Traceback" not in call.args[0] for call in self.panel.call_args_list))
        self.assertTrue(all(call.kwargs.get("notifyUser") is False for call in self.panel.call_args_list))
        self.assertTrue(any(call.args[2] == Qgis.MessageLevel.Critical for call in self.panel.call_args_list))

    def test_log_directory_or_file_open_failure_does_not_mask_workflow_error(self):
        for target in ("os.makedirs", "RotatingFileHandler"):
            with self.subTest(target=target), patch(
                    "savonia_responsible_forest_planning_tool.app_logging." + target,
                    side_effect=PermissionError("controlled log failure")):
                app_logging.configure_logging()
                with self.assertRaises(QgsProcessingException) as error:
                    workflow.run_workflow({"language": "en"})
                self.assertNotIn("controlled log failure", str(error.exception))
                self.assertIn("input_validation", str(error.exception))
                app_logging.shutdown_logging()
        self.assertTrue(self.panel.called)


if __name__ == "__main__":
    unittest.main()
