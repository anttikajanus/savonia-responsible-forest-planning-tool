"""Managed WFS startup must inspect schemas without reading feature data."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


from qgis_test_environment import qgis_application

APP = qgis_application()

from qgis.core import (Qgis, QgsApplication, QgsDataSourceUri, QgsFeatureRequest,
                       QgsFillSymbol, QgsMapRendererParallelJob, QgsMapSettings,
                       QgsProject, QgsRectangle, QgsSettings, QgsSingleSymbolRenderer, QgsVectorLayer)
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtGui import QColor


from savonia_responsible_forest_planning_tool.adapters import project_setup, sources
from savonia_responsible_forest_planning_tool.analysis.worker_task import (
    capture_worker_inputs, ResponsibleForestPlanningAnalysisTask,
)
from savonia_responsible_forest_planning_tool.i18n import tr
from wfs_fixture import LocalWfs
from workflow_fixture import fixture_sources, source_record


def feature_requests(fixture):
    return [query for query in fixture.requests
            if query.get("request", "").lower() == "getfeature"]


class WfsInitializationTests(unittest.TestCase):
    def test_setup_upgrades_existing_connection_and_preserves_identity_and_filter(self):
        service_id = "forest_centre_stand"
        fields = fixture_sources()[service_id]
        with LocalWfs({service_id: fields}, version="2.0.0") as fixture:
            definition = {**sources.SERVICE_DEFINITIONS[service_id], "endpoint": fixture.endpoint,
                          "feature_type": "fixture:" + service_id}
            uri = QgsDataSourceUri()
            for key, value in {
                "url": fixture.endpoint, "typename": "fixture:" + service_id,
                "version": "2.0.0", "forceInitialGetFeature": "true",
                "maxNumFeatures": "1",
                "filter": "VOLUME > 0", "srsname": "EPSG:3067",
            }.items():
                uri.setParam(key, value)
            layer = QgsVectorLayer(uri.uri(), "old stand", "WFS")
            self.assertTrue(layer.isValid())
            layer.setCustomProperty("savonia/service_id", service_id)
            layer.setCustomProperty("savonia/feature_type", "fixture:" + service_id)
            project = QgsProject()
            self.addCleanup(project.clear)
            project.addMapLayer(layer, False)
            group = project.layerTreeRoot().addGroup("sources")
            group.addLayer(layer).setItemVisibilityChecked(False)
            original_id = layer.id()
            fixture.requests.clear()
            with patch.dict(sources.SERVICE_DEFINITIONS, {service_id: definition}):
                for language in ("fi", "en"):
                    reused, status = project_setup._add_or_relabel_wfs(project, group, service_id, language)
                    self.assertIs(reused, layer)
                    self.assertEqual(reused.id(), original_id)
                    self.assertEqual(status["status"], "AVAILABLE")
                    upgraded = QgsDataSourceUri(reused.source())
                    self.assertEqual(upgraded.param("filter"), "VOLUME > 0")
                    self.assertEqual(upgraded.param("srsname"), "EPSG:3067")
                    self.assertFalse(upgraded.hasParam("maxNumFeatures"))
                    self.assertFalse(group.children()[0].itemVisibilityChecked())
                    self.assertEqual(feature_requests(fixture), [])
                    self.assertTrue(all(query.get("version") == "2.0.0" for query in fixture.requests))

    def test_managed_setup_and_worker_reopen_do_not_read_features(self):
        fields = fixture_sources()
        with LocalWfs(fields, version="2.0.0") as fixture:
            definitions = {
                key: {**value, "endpoint": fixture.endpoint, "feature_type": "fixture:" + key}
                for key, value in sources.SERVICE_DEFINITIONS.items()
            }
            # Exercise the provider's generic Surface geometry declaration too,
            # matching the cached Forest Centre schemas.
            schema = fixture.schema
            fixture.schema = lambda key: schema(key).replace("gml:PolygonPropertyType", "gml:SurfacePropertyType")
            with patch.dict(sources.SERVICE_DEFINITIONS, definitions):
                project = QgsProject()
                self.addCleanup(project.clear)
                group = project.layerTreeRoot().addGroup("sources")
                identities = {}
                for language in ("en", "fi", "en"):
                    for service_id in definitions:
                        layer, status = project_setup._add_or_relabel_wfs(project, group, service_id, language)
                        self.assertEqual(status["status"], "AVAILABLE", status)
                        self.assertEqual(layer.geometryType(), Qgis.GeometryType.Polygon)
                        self.assertTrue(layer.crs().isValid())
                        self.assertEqual(layer.name(), tr(language, definitions[service_id]["name_key"]))
                        identities.setdefault(service_id, layer.id())
                        self.assertEqual(layer.id(), identities[service_id])
                        uri = QgsDataSourceUri(layer.source())
                        self.assertEqual(uri.param("skipInitialGetFeature"), "true")
                        self.assertEqual(uri.param("forceInitialGetFeature"), "false")
                        self.assertEqual(uri.param("restrictToRequestBBOX"), "1")
                        self.assertEqual(uri.param("pageSize"), "1000")
                        self.assertFalse(uri.hasParam("maxNumFeatures"))
                    QgsApplication.processEvents()
                    self.assertEqual(feature_requests(fixture), [])
                aoi = QgsVectorLayer("Polygon?crs=EPSG:3067", "AOI", "memory")
                layers = {layer.customProperty("savonia/service_id"): layer
                          for layer in project.mapLayers().values()}
                captured = capture_worker_inputs(aoi, layers, False, project.transformContext(), "en", "unused", sawlog_price_eur_m3=75.25)
                worker_layers = ResponsibleForestPlanningAnalysisTask._construct_sources(captured["sources"])
                self.assertTrue(all(layer.isValid() for layer in worker_layers.values()))
                self.assertEqual(feature_requests(fixture), [])
                with tempfile.TemporaryDirectory() as folder:
                    filename = str(Path(folder) / "sources.qgs")
                    self.assertTrue(project.write(filename))
                    reopened = QgsProject()
                    try:
                        self.assertTrue(reopened.read(filename))
                        self.assertEqual(len(reopened.mapLayers()), len(definitions))
                        self.assertTrue(all(layer.isValid() for layer in reopened.mapLayers().values()))
                        self.assertEqual(feature_requests(fixture), [])
                    finally:
                        reopened.clear()

    def test_first_and_cached_map_render_fetch_only_the_view_extent(self):
        service_id = "forest_centre_stand"
        with LocalWfs({service_id: fixture_sources()[service_id]}, version="2.0.0") as fixture:
            layer = QgsVectorLayer(sources.qgis_wfs_uri({
                "endpoint": fixture.endpoint, "feature_type": "fixture:" + service_id,
            }), "stand", "WFS")
            self.assertTrue(layer.isValid())
            self.assertEqual(feature_requests(fixture), [])
            layer.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple({"color": "red"})))
            settings = QgsMapSettings()
            settings.setLayers([layer])
            settings.setDestinationCrs(layer.crs())
            settings.setExtent(QgsRectangle(349990, 6899990, 350110, 6900110))
            settings.setOutputSize(QSize(100, 100))
            settings.setBackgroundColor(QColor("white"))
            for _render in range(2):
                job = QgsMapRendererParallelJob(settings)
                job.start()
                job.waitForFinished()
                self.assertEqual(job.renderedImage().pixelColor(50, 50), QColor("red"), feature_requests(fixture))
            self.assertTrue(feature_requests(fixture))
            self.assertTrue(all("bbox" in query for query in feature_requests(fixture)))

    def test_later_bounded_read_pages_beyond_the_startup_page_size(self):
        service_id = "forest_centre_gridcell"
        fields = fixture_sources()[service_id]
        records = [source_record({**fields, "GRIDCELLID": "cell-" + str(index)}) for index in range(1001)]
        with LocalWfs({service_id: fields}, records={service_id: records}, version="2.0.0") as fixture:
            layer = QgsVectorLayer(sources.qgis_wfs_uri({
                "endpoint": fixture.endpoint, "feature_type": "fixture:" + service_id,
                "source_crs": "EPSG:3067",
            }), "grid", "WFS")
            self.assertTrue(layer.isValid())
            self.assertEqual(feature_requests(fixture), [])
            bounds = QgsRectangle(350000, 6900000, 350100, 6900100)
            # Match the shared workflow's AOI-bounded cache initialization.
            layer.getFeatures(QgsFeatureRequest().setFilterFids([]).setFilterRect(bounds).setLimit(0)).close()
            request = QgsFeatureRequest().setFilterRect(bounds)
            cells = list(layer.getFeatures(request))
            self.assertEqual(len(cells), 1001, feature_requests(fixture))
            self.assertEqual({cell["GRIDCELLID"] for cell in cells},
                             {"cell-" + str(index) for index in range(1001)})
            queries = feature_requests(fixture)
            self.assertTrue(all("bbox" in query for query in queries))
            pages = [query for query in queries if query.get("resulttype", "").lower() != "hits"]
            self.assertEqual([int(query.get("startindex", 0)) for query in pages], [0, 1000])
            self.assertTrue(all(query.get("count") == "1000" for query in pages))


if __name__ == "__main__":
    unittest.main()
