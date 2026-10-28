"""WMTS authentication, national CRS, default stack and saved-project behavior."""

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.environ.get(
    "RESPONSIBLE_FOREST_PLANNING_TEST_PLUGIN_ROOT",
    os.environ.get("SAVONIA_TEST_PLUGIN_ROOT", str(Path(__file__).resolve().parents[2])),
))

from qgis.core import (
    QgsApplication, QgsCoordinateReferenceSystem, QgsMapRendererParallelJob,
    QgsMapSettings, QgsProject, QgsRasterLayer, QgsRectangle, QgsVectorLayer,
)
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtGui import QColor

APP = QgsApplication.instance()
if APP is None:
    APP = QgsApplication([], True)
    APP.initQgis()

from savonia_responsible_forest_planning_tool.adapters import project_setup, sources
from savonia_responsible_forest_planning_tool.i18n import tr
from wmts_fixture import LocalWmts


class BasemapSetupTests(unittest.TestCase):
    def setUp(self):
        self.project = QgsProject()
        self.addCleanup(self.project.clear)
        self.fixture = self.enterContext(LocalWmts())
        self.enterContext(patch.object(sources, "MML_WMTS_CAPABILITIES", self.fixture.capabilities_url))
        self.enterContext(patch.object(sources, "mml_api_key", return_value=self.fixture.key))
        # OSM is unrelated to the national WMTS; never contact its public tiles.
        osm = QgsVectorLayer("Polygon?crs=EPSG:3067", "OSM", "memory")
        osm.setCustomProperty("savonia/layer_id", "osm_xyz")
        self.project.addMapLayer(osm)

    def setup_maps(self, language="fi"):
        group = project_setup.ensure_group_order(self.project, language)["basemaps"]
        statuses = project_setup._setup_basemaps(self.project, group, language)
        QgsApplication.processEvents()
        QgsApplication.processEvents()
        return group, statuses

    def test_national_grid_default_order_and_authenticated_tile_rendering(self):
        group, statuses = self.setup_maps()
        self.assertEqual(statuses, [])
        self.assertEqual([node.name() for node in group.children()],
                         ["Ortokuva", "Maastokartta", "OpenStreetMap"])
        self.assertEqual([node.itemVisibilityChecked() for node in group.children()], [False, True, False])
        self.assertEqual(self.fixture.rejected, [])
        for node in group.children()[:2]:
            layer = node.layer()
            self.assertIsInstance(layer, QgsRasterLayer)
            self.assertEqual(layer.crs().authid(), "EPSG:3067")
            uri = parse_qs(layer.source())
            self.assertEqual(uri["tileMatrixSet"], ["ETRS-TM35FIN"])
            self.assertEqual(uri["styles"], ["default"])
            self.assertEqual(uri["username"], [self.fixture.key])
            product = uri["layers"][0]
            self.assertEqual(uri["format"], ["image/jpeg" if product == "ortokuva" else "image/png"])
            settings = QgsMapSettings()
            settings.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:3067"))
            settings.setExtent(QgsRectangle(0, 6500000, 600000, 7100000))
            settings.setOutputSize(QSize(128, 128))
            settings.setBackgroundColor(QColor("white"))
            settings.setLayers([layer])
            job = QgsMapRendererParallelJob(settings)
            job.start()
            job.waitForFinished()
            self.assertFalse(job.errors(), job.errors())
            self.assertNotEqual(job.renderedImage().pixelColor(64, 64), QColor("white"))
            self.assertTrue(any("/" + product + "/default/ETRS-TM35FIN/" in path
                                for path in self.fixture.requests))
        self.assertEqual(self.fixture.rejected, [])

    def test_repeated_setup_preserves_choices_user_layers_ids_and_saved_connections(self):
        group, statuses = self.setup_maps()
        self.assertFalse(statuses)
        original_ids = set(self.project.mapLayers())
        ortho, topo, osm = group.children()
        ortho.setItemVisibilityChecked(True)
        topo.setItemVisibilityChecked(False)
        osm.setItemVisibilityChecked(True)
        user = QgsVectorLayer("Polygon?crs=EPSG:3067", "User map", "memory")
        self.project.addMapLayer(user, False)
        group.insertLayer(0, user).setItemVisibilityChecked(False)
        # Move the managed orthophoto elsewhere, retaining its visibility.
        project_setup._place_layer_in_group(self.project, self.project.layerTreeRoot(), ortho.layer())
        for language in ("en", "fi"):
            group, statuses = self.setup_maps(language)
            self.assertFalse(statuses)
            self.assertEqual(set(self.project.mapLayers()), original_ids | {user.id()})
            self.assertEqual([node.name() for node in group.children()[:3]],
                             [tr(language, key) for key in ("orthophoto_layer", "topographic_layer", "osm_layer")])
            self.assertEqual([node.itemVisibilityChecked() for node in group.children()], [True, False, True, False])
        with tempfile.TemporaryDirectory() as folder:
            filename = str(Path(folder) / "basemaps.qgs")
            self.assertTrue(self.project.write(filename))
            reopened = QgsProject()
            try:
                self.assertTrue(reopened.read(filename))
                saved = reopened.layerTreeRoot().findGroup("Taustakartat")
                self.assertEqual([node.itemVisibilityChecked() for node in saved.children()[:3]], [True, False, True])
                for node in saved.children()[:2]:
                    self.assertTrue(node.layer().isValid())
                    self.assertEqual(node.layer().crs().authid(), "EPSG:3067")
                    self.assertEqual(parse_qs(node.layer().source())["username"], [self.fixture.key])
            finally:
                reopened.clear()
        self.assertEqual(self.fixture.rejected, [])

    def test_invalid_wmts_is_reported_in_both_languages_and_retry_adds_default(self):
        self.fixture.fail = True
        for language in ("fi", "en"):
            group, statuses = self.setup_maps(language)
            self.assertEqual(len(statuses), 2)
            self.assertEqual(len(group.children()), 1)
            self.assertTrue(group.children()[0].itemVisibilityChecked())
            for status, key in zip(statuses, ("orthophoto_layer", "topographic_layer")):
                self.assertEqual(status["status"], "INVALID_LAYER")
                self.assertEqual(status["message"], tr(language, "basemap_unavailable", layer=tr(language, key)))
        self.fixture.fail = False
        group, statuses = self.setup_maps()
        self.assertFalse(statuses)
        self.assertEqual([node.itemVisibilityChecked() for node in group.children()], [False, True, False])

    def test_changed_key_reconnects_in_place_and_missing_orthophoto_is_recreated_hidden(self):
        group, statuses = self.setup_maps()
        self.assertFalse(statuses)
        original_ids = [node.layerId() for node in group.children()]
        group.children()[0].setItemVisibilityChecked(True)
        group.children()[1].setItemVisibilityChecked(False)
        self.fixture.key = "replacement-key"
        with patch.object(sources, "mml_api_key", return_value=self.fixture.key):
            group, statuses = self.setup_maps("en")
            self.assertFalse(statuses)
            self.assertEqual([node.layerId() for node in group.children()], original_ids)
            self.assertEqual([node.itemVisibilityChecked() for node in group.children()], [True, False, False])
            for node in group.children()[:2]:
                self.assertEqual(parse_qs(node.layer().source())["username"], ["replacement-key"])
            self.project.removeMapLayer(original_ids[0])
            group, statuses = self.setup_maps("fi")
            self.assertFalse(statuses)
            self.assertNotEqual(group.children()[0].layerId(), original_ids[0])
            self.assertEqual([node.layerId() for node in group.children()[1:]], original_ids[1:])
            self.assertEqual([node.itemVisibilityChecked() for node in group.children()], [False, False, False])
        self.assertEqual(self.fixture.rejected, [])
