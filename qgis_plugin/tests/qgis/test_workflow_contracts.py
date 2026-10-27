"""Selection, preflight and WFS 2.0 regressions at the shared workflow seam."""

import json
import os
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, os.environ.get(
    "RESPONSIBLE_FOREST_PLANNING_TEST_PLUGIN_ROOT",
    os.environ.get("SAVONIA_TEST_PLUGIN_ROOT", str(Path(__file__).resolve().parents[2])),
))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qgis.core import (Qgis, QgsApplication, QgsFeature, QgsFeatureRequest, QgsGeometry,
                       QgsProcessingException, QgsProject, QgsRectangle, QgsVectorLayer)
from qgis.PyQt.QtTest import QTest

APP = QgsApplication.instance()
if APP is None:
    APP = QgsApplication([], False)
    APP.initQgis()

from savonia_responsible_forest_planning_tool.analysis.worker_task import (
    capture_worker_inputs, ResponsibleForestPlanningAnalysisTask,
)
from savonia_responsible_forest_planning_tool.analysis import workflow
from savonia_responsible_forest_planning_tool.i18n import tr
from workflow_fixture import WorkflowFixtureMixin, fixture_sources, source_record


class WorkflowContractTests(WorkflowFixtureMixin, unittest.TestCase):
    def test_fixture_priming_keeps_initial_source_reads_aoi_bounded(self):
        initial_requests = {}
        bounds = QgsRectangle(350000, 6900000, 350100, 6900100)

        def source_layer(*args, **kwargs):
            layer = QgsVectorLayer(*args, **kwargs)
            if layer.providerType() != "WFS":
                return layer
            get_features = layer.getFeatures

            def read_features(request=None):
                layer.getFeatures = get_features
                if request is None:
                    # Reproduce hosted QGIS's populated initial read using
                    # real provider features, independent of local defaults.
                    list(get_features())
                    return get_features(QgsFeatureRequest().setFilterRect(bounds))
                initial_requests[layer.name()] = request
                return get_features(request)

            layer.getFeatures = read_features
            return layer

        with patch("workflow_fixture.QgsVectorLayer", side_effect=source_layer):
            with self.scenario([], prime=True) as (_, layers, aoi):
                self.assertEqual(set(initial_requests), set(fixture_sources()))
                for request in initial_requests.values():
                    self.assertEqual(request.filterType(), Qgis.FeatureRequestFilterType.Fids)
                    self.assertFalse(request.filterFids())
                    self.assertEqual(request.limit(), 0)
                    self.assertEqual(request.filterRect(), aoi.extent())
                result = self.run_algorithm(layers, aoi, "en", "populated-initial-read")
                published = QgsVectorLayer(result["RESULT"], "result", "ogr")
                self.assertTrue(published.isValid())
                feature, = list(published.getFeatures())
                self.assertEqual(feature["total_volume_m3_ha"], 200)

    def test_selected_source_snapshot_survives_validation_and_later_selection_changes(self):
        fields = fixture_sources()
        stands = [source_record(fields["forest_centre_stand"]),
                  source_record({**fields["forest_centre_stand"], "standid": "unselected", "VOLUME": 999},
                                x=350025, width=50)]
        for language in ("en", "fi"):
            outputs = []
            for entry in ("processing", "worker"):
                with self.subTest(language=language, entry=entry), self.scenario([], stands, prime=True) as (fixture, layers, aoi):
                    stand = layers["forest_centre_stand"]
                    features = list(stand.getFeatures(QgsFeatureRequest().setFilterRect(aoi.extent())))
                    selected = next(feature for feature in features if feature["standid"] == "stand-1")
                    stand.selectByIds([selected.id()])
                    if entry == "processing":
                        result = self.run_algorithm(layers, stand, language, "selected-processing-" + language,
                                                    selected_only=True)
                        uri = result["RESULT"]
                    else:
                        snapshot = capture_worker_inputs(stand, layers, True, QgsProject.instance().transformContext(),
                                                         language, self.temp.name, "selected-worker-" + language)
                        self.assertEqual(len(snapshot["selected_source_feature_snapshots"]["forest_centre_stand"]), 1)
                        stand.selectByIds([feature.id() for feature in features if feature.id() != selected.id()])
                        # Captured attributes and geometry must survive remote changes too.
                        fixture.records["forest_centre_stand"] = [source_record({
                            **fields["forest_centre_stand"], "VOLUME": 777})]
                        fixture.feature_failures.add("forest_centre_stand")
                        completed = []
                        task = ResponsibleForestPlanningAnalysisTask("selection fixture", snapshot,
                            lambda finished, success: completed.append(success))
                        QgsApplication.taskManager().addTask(task)
                        deadline = time.monotonic() + 30
                        while not completed and time.monotonic() < deadline:
                            APP.processEvents()
                            QTest.qWait(5)
                        self.assertEqual(completed, [True], str(task.error))
                        uri = task.result["gpkg_path"] + "|layername=classified_forest_polygons"
                        self.assertTrue(task.result["run_metadata"]["parameters"]["selected_features_only"])
                    layer = QgsVectorLayer(uri, entry, "ogr")
                    row, = list(layer.getFeatures())
                    outputs.append({name: row[name] for name in ("source_stand_id", "area_ha",
                        "total_volume_m3_ha", "source_ids", "indicator_coverage")})
                    self.assertEqual(row["source_stand_id"], "stand-1")
                    self.assertEqual(row["total_volume_m3_ha"], 200)
            self.assertEqual(outputs[0], outputs[1])

    def test_preflight_rejects_bad_inputs_before_retrieval_or_output_mutation(self):
        with self.scenario([]) as (_, layers, aoi):
            empty = QgsVectorLayer("Polygon?crs=EPSG:3067", "empty", "memory")
            invalid = QgsVectorLayer("Polygon?crs=EPSG:3067", "invalid", "memory")
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromWkt("POLYGON ((0 0,2 2,0 2,2 0,0 0))"))
            self.assertTrue(invalid.dataProvider().addFeatures([feature])[0])
            for language in ("en", "fi"):
                base = {"language": language, "sources": layers, "aoi_layer": aoi,
                        "transform_context": QgsProject.instance().transformContext(),
                        "output_folder": self.temp.name, "output_name": "preflight"}
                cases = (
                    ({"aoi_layer": empty}, "error_aoi_empty", {}),
                    ({"aoi_layer": aoi, "selected_only": True}, "error_aoi_empty", {}),
                    ({"aoi_layer": invalid}, "error_aoi_invalid", {"feature_id": next(invalid.getFeatures()).id()}),
                    ({"transform_context": None}, "error_transform_context", {}),
                    ({"output_name": "../escape"}, "error_output_name", {}),
                    ({"output_name": "."}, "error_output_name", {}),
                    ({"output_folder": ""}, "error_output_folder", {}),
                )
                for changes, key, values in cases:
                    with self.subTest(language=language, changes=changes), patch.object(workflow, "retrieve_sources") as retrieve, \
                            patch.object(workflow, "write_outputs") as write:
                        with self.assertRaises(QgsProcessingException) as error:
                            workflow.run_workflow({**base, **changes})
                        self.assertIn(tr(language, key, **values), str(error.exception))
                        retrieve.assert_not_called()
                        write.assert_not_called()
                with patch("savonia_responsible_forest_planning_tool.analysis.workflow_steps.validation.os.access", return_value=False), \
                        patch.object(workflow, "retrieve_sources") as retrieve:
                    with self.assertRaises(QgsProcessingException) as error:
                        workflow.run_workflow(base)
                    self.assertIn(tr(language, "error_output_writable", path=self.temp.name), str(error.exception))
                    retrieve.assert_not_called()
                broken_sources = {**layers, "forest_centre_habitat": None, "forest_centre_gridcell": None}
                with patch.object(workflow, "retrieve_sources") as retrieve:
                    with self.assertRaises(QgsProcessingException) as error:
                        workflow.run_workflow({**base, "sources": broken_sources})
                    self.assertIn(tr(language, "habitat_layer"), str(error.exception))
                    self.assertIn(tr(language, "gridcell_layer"), str(error.exception))
                    retrieve.assert_not_called()
                for extension in ("gpkg", "xlsx"):
                    sentinel = Path(self.temp.name, "preflight." + extension)
                    sentinel.write_bytes(b"previous user output")
                    try:
                        with patch.object(workflow, "retrieve_sources") as retrieve, patch.object(workflow, "write_outputs") as write:
                            with self.assertRaises(QgsProcessingException) as error:
                                workflow.run_workflow(base)
                            self.assertIn(tr(language, "error_output_exists"), str(error.exception))
                            self.assertEqual(sentinel.read_bytes(), b"previous user output")
                            retrieve.assert_not_called()
                            write.assert_not_called()
                    finally:
                        sentinel.unlink()
            self.assertEqual(list(Path(self.temp.name).iterdir()), [])

    def test_wfs2_production_uri_pages_all_cells_with_bounded_requests(self):
        fields = fixture_sources()["forest_centre_gridcell"]
        grid = [source_record({**fields, "GRIDCELLID": "cell-" + str(index), "VOLUME": 100 * (index + 1)},
                              x=350000 + index * 20, width=20) for index in range(5)]
        for language in ("en", "fi"):
            with self.subTest(language=language), self.scenario(grid, version="2.0.0", page_size=2, prime=False) as (fixture, layers, aoi):
                result = self.run_algorithm(layers, aoi, language, "wfs2-" + language)
                layer = QgsVectorLayer(result["RESULT"], "result", "ogr")
                row, = list(layer.getFeatures())
                self.assertEqual(row["grid_total_volume_m3_ha"], 300)
                snapshot = QgsVectorLayer(result["RESULT"].split("|", 1)[0] + "|layername=forest_centre_gridcell", "snapshot", "ogr")
                self.assertEqual({feature["GRIDCELLID"] for feature in snapshot.getFeatures()},
                                 {"cell-" + str(index) for index in range(5)})
                self.assertEqual(snapshot.featureCount(), 5)
                requests = [query for query in fixture.requests if query.get("request", "").lower() == "getfeature"]
                pages = [query for query in requests if query.get("typenames", "").endswith("forest_centre_gridcell")
                         and query.get("resulttype", "").lower() != "hits" and query.get("count") != "1"]
                self.assertEqual([int(query.get("startindex", 0)) for query in pages], [0, 2, 4])
                self.assertTrue(all(query.get("version") == "2.0.0" for query in requests))
                # QGIS may probe geometry with COUNT=1 while constructing a provider.
                # All paged analysis reads must be spatially bounded.
                self.assertTrue(all("bbox" in query or query.get("count") == "1" for query in requests))
                self.assertTrue(all("bbox" in query for query in pages))

    def test_wfs2_empty_success_differs_from_later_page_failure(self):
        fields = fixture_sources()["forest_centre_gridcell"]
        grid = [source_record({**fields, "GRIDCELLID": "cell-" + str(index)},
                              x=350000 + index * 20, width=20) for index in range(3)]
        for language in ("en", "fi"):
            with self.subTest(language=language), self.scenario([], version="2.0.0", prime=False) as (_, layers, aoi):
                result = self.run_algorithm(layers, aoi, language, "empty-wfs2-" + language)
                layer = QgsVectorLayer(result["RESULT"], "empty grid", "ogr")
                row, = list(layer.getFeatures())
                self.assertEqual(json.loads(row["indicator_status"])["grid_total_volume_m3_ha"], "UNKNOWN_FIELD_OR_VALUE")
            with self.scenario(grid, version="2.0.0", page_size=2, prime=False) as (fixture, layers, aoi):
                fixture.page_failures.add(("forest_centre_gridcell", 2))
                name = "failed-page-" + language
                with self.assertRaises(QgsProcessingException) as error:
                    self.run_algorithm(layers, aoi, language, name)
                self.assertIn("forest_centre_gridcell", str(error.exception))
                self.assertTrue(any(int(query.get("startindex", 0)) == 2 for query in fixture.requests))
                self.assertEqual(list(Path(self.temp.name).glob(name + ".*")), [])


if __name__ == "__main__":
    unittest.main()
