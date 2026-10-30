"""MML key gate, real OAPIF requests, parcel presentation and persistence."""

import base64
from pathlib import Path
import tempfile
import unittest
from urllib.parse import quote, quote_plus
from unittest.mock import patch


from qgis_test_environment import qgis_application

APP = qgis_application()

from qgis.core import (
    Qgis, QgsApplication, QgsDataSourceUri, QgsFeatureRequest, QgsMapRendererParallelJob, QgsMapSettings,
    QgsProject, QgsRectangle, QgsSettings, QgsVectorLayer,
)
from qgis.PyQt.QtCore import QSize, Qt
from qgis.PyQt.QtWidgets import QInputDialog, QLineEdit


from savonia_responsible_forest_planning_tool.adapters import project_setup, sources
from savonia_responsible_forest_planning_tool.i18n import tr
from savonia_responsible_forest_planning_tool.ui.plugin import ResponsibleForestPlanningPlugin
from oapif_fixture import LocalOapif
from ui_fixture import Interface


class ParcelReferenceTests(unittest.TestCase):
    def setUp(self):
        # Keep personal QGIS credentials untouched and isolate deterministic tests.
        self.setting_key = "savonia-test/mml-parcel-key"
        self.enterContext(patch.object(sources, "MML_API_KEY_SETTING_KEY", self.setting_key))
        self.enterContext(patch("savonia_responsible_forest_planning_tool.ui.plugin.MML_API_KEY_SETTING_KEY", self.setting_key))
        QgsSettings().remove(self.setting_key)
        self.addCleanup(QgsSettings().remove, self.setting_key)
        self.project = QgsProject()
        self.addCleanup(self.project.clear)

    def test_missing_key_stops_before_project_mutation_or_network(self):
        user = QgsVectorLayer("Polygon?crs=EPSG:3067", "user", "memory")
        self.project.addMapLayer(user)
        before = self.project.layerTreeRoot().dump()
        with patch.object(project_setup, "inspect_service") as discover, patch.object(project_setup, "_setup_parcels") as parcels:
            for language in ("en", "fi"):
                result = project_setup.setup_project(self.project, language)
                self.assertFalse(result["ready"])
                self.assertEqual(result["sources"][0]["message"], tr(language, "mml_key_required"))
                self.assertEqual(self.project.layerTreeRoot().dump(), before)
            discover.assert_not_called()
            parcels.assert_not_called()

    def test_saved_key_authenticates_discovery_without_rejected_requests(self):
        with LocalOapif() as fixture:
            fixture.challenge_auth = True
            QgsSettings().setValue(self.setting_key, fixture.key)
            self.enterContext(patch.object(sources, "MML_PARCEL_ENDPOINT", fixture.endpoint))
            group = project_setup.ensure_group_order(self.project, "en")["references"]
            for language in ("en", "fi"):
                statuses = project_setup._setup_parcels(self.project, group, language)
                self.assertEqual([row["status"] for row in statuses], ["AVAILABLE", "AVAILABLE"])
            self.assertEqual(fixture.unauthorized_paths, [],
                             "A request without the saved key triggers MML's authentication dialog")
            self.assertIn("/conformance", fixture.basic_authenticated_paths)
            self.assertTrue(all(not query.get("api-key") for _path, query in fixture.requests))

    def test_oapif_authentication_bbox_style_reuse_and_saved_project(self):
        with LocalOapif() as fixture:
            QgsSettings().setValue(self.setting_key, fixture.key)
            self.enterContext(patch.object(sources, "MML_PARCEL_ENDPOINT", fixture.endpoint))
            references = project_setup.ensure_group_order(self.project, "en")["references"]
            groups = project_setup._reference_groups(self.project, references, "en")
            group = groups["properties"]
            user = QgsVectorLayer("Polygon?crs=EPSG:3067", "user", "memory")
            self.project.addMapLayer(user, False)
            group.addLayer(user)
            for language in ("en", "fi", "en"):
                for item in self.project.mapLayers().values():
                    if item.customProperty("savonia/service_id") in (
                            sources.MML_PARCEL_SERVICE_ID, sources.MML_IDENTIFIER_SERVICE_ID):
                        item.setMinimumScale(500000)
                        item.setMaximumScale(100)
                        item.setScaleBasedVisibility(False)
                statuses = project_setup._setup_parcels(self.project, group, language)
                self.assertEqual([row["status"] for row in statuses], ["AVAILABLE", "AVAILABLE"], statuses)
                project_setup._order_reference_layers(self.project, groups)
                QgsApplication.processEvents()
                QgsApplication.processEvents()
                layer = group.children()[0].layer()
                labels = group.children()[1].layer()
                self.assertEqual(layer.name(), tr(language, "parcel_layer"))
                self.assertEqual(layer.providerType(), "oapif")
                self.assertEqual(QgsDataSourceUri(layer.source()).username(), fixture.key)
                self.assertEqual(QgsDataSourceUri(layer.source()).password(), "")
                self.assertEqual(labels.name(), tr(language, "property_identifier_layer"))
                self.assertEqual(len(self.project.mapLayers()), 3)
                self.assertEqual(group.children()[2].layerId(), user.id())
                symbol = layer.renderer().symbol().symbolLayer(0)
                self.assertEqual(symbol.brushStyle(), Qt.BrushStyle.NoBrush)
                self.assertEqual(symbol.strokeColor().name(), "#ff0000")
                self.assertAlmostEqual(symbol.strokeWidth(), 1.0)
                self.assertEqual(symbol.strokeWidthUnit(), Qgis.RenderUnit.Millimeters)
                self.assertFalse(layer.labelsEnabled())
                self.assertIsNone(layer.labeling())
                self.assertEqual(labels.renderer().type(), "nullSymbol")
                self.assertTrue(labels.labelsEnabled())
                for item, limit in ((layer, 25000), (labels, 10000)):
                    self.assertTrue(item.hasScaleBasedVisibility())
                    self.assertTrue(item.isInScaleRange(1000))
                    self.assertTrue(item.isInScaleRange(10000))
                    self.assertTrue(item.isInScaleRange(limit))
                    self.assertFalse(item.isInScaleRange(limit + 0.001))
                    self.assertEqual(item.isInScaleRange(25000), item == layer)
                    self.assertFalse(item.isInScaleRange(500000))
                settings = labels.labeling().settings()
                self.assertEqual(settings.fieldName, "kiinteistotunnuksenEsitysmuoto")
                self.assertFalse(settings.isExpression)
                text_format = settings.format()
                self.assertEqual(text_format.color().name(), "#ff0000")
                self.assertEqual(text_format.size(), 20)
                buffer = text_format.buffer()
                self.assertTrue(buffer.enabled())
                self.assertEqual(buffer.size(), 2)
                self.assertEqual(buffer.sizeUnit(), Qgis.RenderUnit.Millimeters)
                self.assertEqual(buffer.color().name(), "#ffffff")
                self.assertEqual(buffer.opacity(), 1)
                self.assertEqual(buffer.joinStyle(), Qt.PenJoinStyle.RoundJoin)
                self.assertFalse(buffer.fillBufferInterior())
                # Move the layer down to exercise restoring its top position.
                node = group.children()[0]
                replacement = node.clone()
                group.addChildNode(replacement)
                group.removeChildNode(node)
                symbol.setStrokeWidth(0.3)  # Repeated setup must restore the managed width.
            bounds = QgsRectangle(24.899, 60.099, 24.911, 60.111)
            settings = QgsMapSettings()
            settings.setLayers([labels, layer])
            settings.setDestinationCrs(layer.crs())
            settings.setExtent(bounds)
            settings.setOutputSize(QSize(600, 600))
            self.assertLessEqual(settings.scale(), 10000, "Render inside the identifier visibility limit")
            job = QgsMapRendererParallelJob(settings)
            job.start()
            job.waitForFinished()
            self.assertEqual([label.labelText for label in job.takeLabelingResults().allLabels()], ["123-456-7-8"])
            cached_job = QgsMapRendererParallelJob(settings)
            cached_job.start()
            cached_job.waitForFinished()
            self.assertEqual([label.labelText for label in cached_job.takeLabelingResults().allLabels()], ["123-456-7-8"])
            feature_requests = [query for path, query in fixture.requests if path.endswith("/items")]
            self.assertTrue(all("bbox" in query or query.get("limit") == ["10"] for query in feature_requests), feature_requests)
            records = list(layer.getFeatures(QgsFeatureRequest().setFilterRect(bounds)))
            self.assertTrue(records, fixture.requests)
            self.assertEqual(records[0]["kiinteistotunnuksenEsitysmuoto"], "123-456-7-8")
            self.assertTrue(any("bbox" in query for _path, query in fixture.requests), fixture.requests)
            self.assertEqual(fixture.unauthorized_paths, [])
            self.assertTrue(all(path in fixture.basic_authenticated_paths for path, _query in fixture.requests))
            layer_id = layer.id()
            QgsSettings().setValue(self.setting_key, "wrong-key")
            self.assertEqual(project_setup._setup_parcels(self.project, group, "en")[0]["status"], "UNAVAILABLE")
            QgsSettings().setValue(self.setting_key, fixture.key)
            self.assertEqual(project_setup._setup_parcels(self.project, group, "en")[0]["status"], "AVAILABLE")
            self.assertEqual(layer.id(), layer_id)
            fixture.unauthorized_paths.clear()
            with tempfile.TemporaryDirectory() as folder:
                filename = str(Path(folder) / "parcels.qgs")
                self.assertTrue(self.project.write(filename))
                restored = QgsProject()
                self.assertTrue(restored.read(filename))
                reloaded = next(item for item in restored.mapLayers().values()
                                if item.customProperty("savonia/service_id") == sources.MML_IDENTIFIER_SERVICE_ID)
                self.assertIn(fixture.key, reloaded.source())
                self.assertEqual(QgsDataSourceUri(reloaded.source()).username(), fixture.key)
                self.assertEqual(QgsDataSourceUri(reloaded.source()).password(), "")
                self.assertEqual(reloaded.renderer().type(), "nullSymbol")
                reloaded_parcels = next(item for item in restored.mapLayers().values()
                                        if item.customProperty("savonia/service_id") == sources.MML_PARCEL_SERVICE_ID)
                saved_symbol = reloaded_parcels.renderer().symbol().symbolLayer(0)
                self.assertAlmostEqual(saved_symbol.strokeWidth(), 1.0)
                self.assertEqual(saved_symbol.strokeWidthUnit(), Qgis.RenderUnit.Millimeters)
                # Qt 5 buffer wrappers borrow their owner; keep the settings alive.
                saved_settings = reloaded.labeling().settings()
                saved_format = saved_settings.format()
                self.assertEqual(saved_format.color().name(), "#ff0000")
                self.assertEqual(saved_format.size(), 20)
                saved_buffer = saved_format.buffer()
                self.assertTrue(saved_buffer.enabled())
                self.assertEqual(saved_buffer.size(), 2)
                self.assertEqual(saved_buffer.sizeUnit(), Qgis.RenderUnit.Millimeters)
                self.assertEqual(saved_buffer.color().name(), "#ffffff")
                self.assertEqual(saved_buffer.opacity(), 1)
                self.assertEqual(saved_buffer.joinStyle(), Qt.PenJoinStyle.RoundJoin)
                self.assertFalse(saved_buffer.fillBufferInterior())
                for item, limit in ((reloaded_parcels, 25000), (reloaded, 10000)):
                    self.assertTrue(item.hasScaleBasedVisibility())
                    self.assertTrue(item.isInScaleRange(1000))
                    self.assertTrue(item.isInScaleRange(10000))
                    self.assertTrue(item.isInScaleRange(limit))
                    self.assertFalse(item.isInScaleRange(limit + 0.001))
                    self.assertEqual(item.isInScaleRange(25000), item == reloaded_parcels)
                    self.assertFalse(item.isInScaleRange(500000))
                self.assertTrue(list(reloaded.getFeatures(QgsFeatureRequest().setFilterRect(bounds))))
                self.assertEqual(fixture.unauthorized_paths, [])
                restored.clear()

    def test_unavailable_schema_and_wrong_geometry_are_reported_then_retry_succeeds(self):
        with LocalOapif() as fixture:
            QgsSettings().setValue(self.setting_key, fixture.key)
            self.enterContext(patch.object(sources, "MML_PARCEL_ENDPOINT", fixture.endpoint))
            group = project_setup.ensure_group_order(self.project, "en")["references"]
            fixture.fail = True
            self.assertEqual(project_setup._setup_parcels(self.project, group, "en")[0]["status"], "UNAVAILABLE")
            fixture.fail = False
            fixture.identifier_label_field = "missing-label"
            self.assertEqual(project_setup._setup_parcels(self.project, group, "fi")[1]["status"], "INVALID_LAYER")
            fixture.identifier_label_field = "kiinteistotunnuksenEsitysmuoto"
            fixture.geometry_type = "Point"
            self.project.clear()
            group = project_setup.ensure_group_order(self.project, "en")["references"]
            self.assertEqual(project_setup._setup_parcels(self.project, group, "en")[0]["status"], "INVALID_LAYER")
            fixture.geometry_type = "Polygon"
            fixture.label_field = "unused-on-polygons"
            self.assertEqual(project_setup._setup_parcels(self.project, group, "fi")[0]["status"], "AVAILABLE")
            fixture.identifier_geometry_type = "Polygon"
            # Force reconnection so the changed fixture schema is read again.
            self.project.clear()
            group = project_setup.ensure_group_order(self.project, "en")["references"]
            self.assertEqual(project_setup._setup_parcels(self.project, group, "fi")[1]["status"], "INVALID_LAYER")
            fixture.identifier_geometry_type = "Point"
            self.assertEqual(project_setup._setup_parcels(self.project, group, "fi")[1]["status"], "AVAILABLE")
            self.assertEqual(len(self.project.mapLayers()), 2)

    def test_credentials_are_redacted_in_raw_and_encoded_errors(self):
        key = "fake key&with'encoding"
        QgsSettings().setValue(self.setting_key, key)
        for value in (key, quote(key, safe=""), quote_plus(key, safe="")):
            self.assertNotIn(value, sources.safe_source_error("Request failed: " + value))
        self.assertEqual(sources.safe_source_error("?api-key=old-key&x=1"), "?api-key=[redacted]&x=1")
        uri = sources.qgis_mml_uri(sources.MML_PARCEL_COLLECTION)
        self.assertNotIn("with", sources.safe_source_error(uri))
        self.assertNotIn("encoding", sources.safe_source_error(uri))
        self.assertEqual(sources.safe_source_error("user='old-key' url='https://example.test/'"),
                         "user='[redacted]' url='https://example.test/'")
        encoded = base64.b64encode((key + ":").encode("utf-8")).decode("ascii")
        self.assertNotIn(encoded, sources.safe_source_error("Authorization: Basic " + encoded))

    def test_setup_prompt_requires_key_saves_it_and_reuses_it_in_both_languages(self):
        iface = Interface()
        self.addCleanup(iface.window.deleteLater)
        plugin = ResponsibleForestPlanningPlugin(iface)
        self.addCleanup(plugin.unload)
        with patch("savonia_responsible_forest_planning_tool.ui.plugin.setup_project", return_value={"ready": True, "sources": []}) as setup, patch("savonia_responsible_forest_planning_tool.ui.plugin.syke_user_id", return_value="fixture-syke-id"):
            for language in ("en", "fi"):
                QgsSettings().remove(self.setting_key)
                with patch.object(QgsApplication, "locale", return_value=language):
                    for answer in (("", False), ("  ", True)):
                        setup.reset_mock()
                        with patch.object(QInputDialog, "getText", return_value=answer):
                            plugin.setup_project_layers()
                        setup.assert_not_called()
                        self.assertEqual(iface.messages[-1][1], tr(language, "mml_key_required"))
                    with patch.object(QInputDialog, "getText", return_value=(" fixture-mml-key ", True)) as prompt:
                        plugin.setup_project_layers()
                        self.assertEqual(prompt.call_args.args[1], tr(language, "mml_key_title"))
                        self.assertEqual(prompt.call_args.args[3], QLineEdit.EchoMode.Password)
                        self.assertEqual(sources.mml_api_key(), "fixture-mml-key")
                        plugin.setup_project_layers()
                        prompt.assert_called_once()


if __name__ == "__main__":
    unittest.main()
