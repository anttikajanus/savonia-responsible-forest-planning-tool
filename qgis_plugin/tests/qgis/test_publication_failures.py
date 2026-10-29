"""Paired artifact cleanup at real GeoPackage and workbook write seams."""

import os
from pathlib import Path
import unittest
from unittest.mock import patch


from qgis_test_environment import qgis_application

APP = qgis_application()

from qgis.core import QgsApplication, QgsProcessingException, QgsProcessingFeedback, QgsVectorFileWriter, QgsVectorLayer


from savonia_responsible_forest_planning_tool.adapters import geopackage_writer
from savonia_responsible_forest_planning_tool.analysis.workflow_steps import publishing
from savonia_responsible_forest_planning_tool.i18n import tr
from workflow_fixture import WorkflowFixtureMixin


class PublicationFailureTests(WorkflowFixtureMixin, unittest.TestCase):
    def test_later_geopackage_layer_failure_removes_already_written_result(self):
        original = QgsVectorFileWriter.writeAsVectorFormatV3
        for language in ("en", "fi"):
            calls = []
            def fail_snapshot(layer, path, context, options):
                calls.append(options.layerName)
                if options.layerName == "forest_centre_stand":
                    self.assertTrue(Path(path).is_file())
                    return (1, "controlled snapshot write failure")
                return original(layer, path, context, options)
            with self.subTest(language=language), self.scenario([]) as (_, layers, aoi), \
                    patch.object(QgsVectorFileWriter, "writeAsVectorFormatV3", side_effect=fail_snapshot):
                with self.assertRaises(QgsProcessingException) as error:
                    self.run_algorithm(layers, aoi, language, "snapshot-failure")
                self.assertIn("controlled snapshot write failure", str(error.exception))
                self.assertEqual(calls[:2], ["classified_forest_polygons", "forest_centre_stand"])
                self.assertEqual(list(Path(self.temp.name).iterdir()), [])

    def test_required_style_persistence_failure_fails_paired_publication(self):
        for language in ("en", "fi"):
            with self.subTest(language=language), self.scenario([]) as (_, layers, aoi), \
                    patch.object(QgsVectorLayer, "saveStyleToDatabaseV2", return_value=(1, "controlled style failure")) as save:
                with self.assertRaises(QgsProcessingException) as error:
                    self.run_algorithm(layers, aoi, language, "style-failure")
                save.assert_called_once()
                self.assertIn("controlled style failure", str(error.exception))
                self.assertEqual(list(Path(self.temp.name).iterdir()), [])

    def test_cancellation_after_workbook_creation_removes_both_completed_files(self):
        original = publishing.write_workbook
        for language in ("en", "fi"):
            feedback = QgsProcessingFeedback()
            def cancel_after_write(*args, **kwargs):
                result = original(*args, **kwargs)
                self.assertEqual(len(list(Path(self.temp.name).glob("late-cancel.*"))), 2)
                feedback.cancel()
                return result
            with self.subTest(language=language), self.scenario([]) as (_, layers, aoi), \
                    patch.object(publishing, "write_workbook", side_effect=cancel_after_write):
                with self.assertRaises(QgsProcessingException) as error:
                    self.run_algorithm(layers, aoi, language, "late-cancel", feedback)
                self.assertIn(tr(language, "error_cancelled"), str(error.exception))
                self.assertLess(feedback.progress(), 100)
                self.assertEqual(list(Path(self.temp.name).iterdir()), [])

    def test_cleanup_failure_preserves_the_original_write_error(self):
        original_remove = os.remove
        def fail_removal(path):
            if str(path).endswith("cleanup-failure.gpkg"):
                raise PermissionError("controlled deletion failure")
            return original_remove(path)
        with self.scenario([]) as (_, layers, aoi), \
                patch.object(publishing, "write_workbook", side_effect=OSError("original workbook failure")), \
                patch.object(publishing.os, "remove", side_effect=fail_removal):
            with self.assertRaises(QgsProcessingException) as error:
                self.run_algorithm(layers, aoi, "en", "cleanup-failure")
            self.assertIn("original workbook failure", str(error.exception))
            self.assertNotIn("controlled deletion failure", str(error.exception))
            self.assertTrue(Path(self.temp.name, "cleanup-failure.gpkg").is_file())
            self.assertFalse(Path(self.temp.name, "cleanup-failure.xlsx").exists())


if __name__ == "__main__":
    unittest.main()
