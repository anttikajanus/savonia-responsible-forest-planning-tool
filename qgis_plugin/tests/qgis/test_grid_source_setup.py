"""Grid readiness and project setup against a tiny local WFS and QGIS runtime."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


from qgis_test_environment import qgis_application

APP = qgis_application()

from qgis.core import Qgis, QgsApplication, QgsProcessing, QgsProject, QgsVectorLayer
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor


from savonia_responsible_forest_planning_tool.adapters.source_layers import (
    source_identifier_field, verify_source_layer,
)
from savonia_responsible_forest_planning_tool.adapters.sources import SERVICE_DEFINITIONS
from savonia_responsible_forest_planning_tool.analysis.worker_task import capture_worker_inputs
from savonia_responsible_forest_planning_tool.adapters.project_setup import setup_project
from savonia_responsible_forest_planning_tool.i18n import tr
from savonia_responsible_forest_planning_tool.processing.provider import ResponsibleForestPlanningInputsAlgorithm
from wfs_fixture import LocalWfs
from oapif_fixture import LocalOapif
from wmts_fixture import LocalWmts


GRID_ID = "forest_centre_gridcell"
GRID_FIELDS = {
    "GridCellId": "cell-1", "VOLUME": 250.0, "VolumePine": 100.0,
    "VolumeSpruce": 80.0, "VolumeDeciduous": 70.0, "Age": 40.0,
    "SoilType": 60, "DrainageState": 6,
}


class GridSourceTest(unittest.TestCase):
    def assert_grid_style(self, project):
        grid = next(layer for layer in project.mapLayers().values()
                    if layer.customProperty("savonia/service_id", "") == GRID_ID)
        symbol = grid.renderer().symbol().symbolLayer(0)
        self.assertEqual(symbol.brushStyle(), Qt.BrushStyle.NoBrush)
        self.assertEqual(symbol.strokeStyle(), Qt.PenStyle.SolidLine)
        self.assertEqual(symbol.strokeColor(), QColor("#006400"))
        self.assertEqual(symbol.strokeWidth(), 0.25)
        self.assertEqual(symbol.strokeWidthUnit(), Qgis.RenderUnit.Millimeters)

    def assert_forest_visibility(self, project):
        for service_id in ("forest_centre_stand", "forest_centre_habitat"):
            layer = next(layer for layer in project.mapLayers().values()
                         if layer.customProperty("savonia/service_id", "") == service_id)
            with self.subTest(service_id=service_id):
                self.assertTrue(layer.hasScaleBasedVisibility())
                self.assertEqual(layer.maximumScale(), 0.0)
                self.assertTrue(layer.isInScaleRange(1000))
                self.assertTrue(layer.isInScaleRange(7763))
                self.assertFalse(layer.isInScaleRange(7763.001))
                self.assertFalse(layer.isInScaleRange(500000))

    def test_grid_provider_fields_are_ready_independently_of_saved_schema(self):
        self.assertIn(GRID_ID, SERVICE_DEFINITIONS)
        with LocalWfs({GRID_ID: GRID_FIELDS}) as fixture:
            definition = {**SERVICE_DEFINITIONS[GRID_ID], "endpoint": fixture.endpoint}
            with patch.dict(SERVICE_DEFINITIONS, {GRID_ID: definition}):
                typename = "fixture:" + GRID_ID
                layer = QgsVectorLayer(
                    "url='{0}' typename='{1}' version='1.0.0' restrictToRequestBBOX='1'".format(
                        fixture.endpoint, typename
                    ), "grid", "WFS",
                )
                self.assertTrue(layer.isValid())
                layer.setCustomProperty("savonia/endpoint", fixture.endpoint)
                layer.setCustomProperty("savonia/feature_type", typename)
                layer.setCustomProperty("savonia/schema_json", '[{"name":"obsolete"}]')
                for language in ("en", "fi"):
                    metadata, error = verify_source_layer(layer, GRID_ID, language)
                    self.assertIsNone(error)
                    self.assertEqual(metadata["field_map"]["volumepine"], "VolumePine")
                    self.assertEqual(metadata["field_map"]["gridcellid"], "GridCellId")
                    self.assertEqual(metadata["properties"], [{"name": "obsolete"}])
                self.assertEqual(source_identifier_field(layer, GRID_ID), "GridCellId")
                aoi = QgsVectorLayer("Polygon?crs=EPSG:3067", "AOI", "memory")
                capture_args = (aoi, {GRID_ID: layer}, False, QgsProject.instance().transformContext(), "en", "unused")
                before = capture_worker_inputs(*capture_args)
                layer.setMinimumScale(300.000001)
                layer.setScaleBasedVisibility(True)
                after = capture_worker_inputs(*capture_args)
                self.assertEqual(before["sources"], after["sources"])
                self.assertEqual(after["sources"][GRID_ID]["properties"]["savonia/feature_type"], typename)

    def test_saved_schema_cannot_replace_missing_required_grid_provider_fields(self):
        incomplete = {key: value for key, value in GRID_FIELDS.items() if key != "VolumeDeciduous"}
        with LocalWfs({GRID_ID: incomplete}) as fixture:
            definition = {**SERVICE_DEFINITIONS[GRID_ID], "endpoint": fixture.endpoint}
            with patch.dict(SERVICE_DEFINITIONS, {GRID_ID: definition}):
                typename = "fixture:" + GRID_ID
                layer = QgsVectorLayer(
                    "url='{0}' typename='{1}' version='1.0.0'".format(fixture.endpoint, typename),
                    "grid", "WFS",
                )
                self.assertTrue(layer.isValid())
                layer.setCustomProperty("savonia/endpoint", fixture.endpoint)
                layer.setCustomProperty("savonia/feature_type", typename)
                layer.setCustomProperty("savonia/schema_json", json.dumps(
                    [{"name": key} for key in GRID_FIELDS]
                ))
                for language in ("en", "fi"):
                    metadata, error = verify_source_layer(layer, GRID_ID, language)
                    self.assertIsNone(metadata)
                    self.assertEqual(error["reason_code"], "REQUIRED_FIELDS_MISSING")
                    self.assertEqual(error["message"], tr(
                        language, "source_schema_fields_missing", fields="volumedeciduous"
                    ))

    def test_setup_reuses_and_moves_grid_below_other_references_in_both_languages(self):
        sources = {
            "forest_centre_stand": {"volume": 200., "sawlogvolume": 100., "volumegrowth": 4., "meanage": 40.},
            "forest_centre_habitat": {"habitattype": "3"},
            "syke_protected_areas_state_owned": {"olotila": "Voimassa", "tyyppilyhenne": "VSA"},
            "syke_protected_areas_private_land": {"olotila": "Voimassa", "kohdetyyppi": "YSA"},
            "syke_protected_areas_wilderness": {"olotila": "Voimassa", "kohdetyyppi": "EMA"},
            "syke_nature_conservation_programme_areas": {"lsoaluetunnus": "programme-1", "luokka": "AMO"},
            "syke_groundwater_areas": {"tunnus": "groundwater-1"},
            GRID_ID: GRID_FIELDS,
        }
        project = QgsProject()
        # An already configured basemap avoids contacting an unrelated XYZ service.
        basemap = QgsVectorLayer("Polygon?crs=EPSG:3067", "basemap", "memory")
        basemap.setCustomProperty("savonia/layer_id", "osm_xyz")
        project.addMapLayer(basemap)
        with LocalWfs(sources) as fixture, LocalOapif() as parcels, LocalWmts() as maps:
            definitions = {
                source: {**definition, "endpoint": fixture.endpoint, "feature_type": "fixture:" + source}
                for source, definition in SERVICE_DEFINITIONS.items()
            }
            with (patch.dict(SERVICE_DEFINITIONS, definitions),
                  patch("savonia_responsible_forest_planning_tool.adapters.sources.MML_WMTS_CAPABILITIES", maps.capabilities_url),
                  patch("savonia_responsible_forest_planning_tool.adapters.sources.mml_api_key", return_value=parcels.key),
                  patch("savonia_responsible_forest_planning_tool.adapters.project_setup.mml_api_key", return_value=parcels.key),
                  patch("savonia_responsible_forest_planning_tool.adapters.sources.MML_PARCEL_ENDPOINT", parcels.endpoint)):
                first = setup_project(project, "en")
                QgsApplication.processEvents()
                QgsApplication.processEvents()
                self.assertTrue(first["ready"], first["sources"])
                self.assert_forest_visibility(project)
                self.assert_grid_style(project)
                references = project.layerTreeRoot().findGroup(tr("en", "references_group"))
                expected = (
                    ("property_group", ("mml_parcels", "mml_property_identifiers")),
                    ("forest_group", ("forest_centre_habitat", "forest_centre_stand", GRID_ID)),
                    ("protected_group", ("syke_nature_conservation_programme_areas",
                                         "syke_protected_areas_wilderness",
                                         "syke_protected_areas_state_owned",
                                         "syke_protected_areas_private_land")),
                    ("water_group", ("syke_groundwater_areas",)),
                )
                original_ids = set(project.mapLayers())
                forest = references.children()[1]
                grid = next(layer for layer in project.mapLayers().values()
                            if layer.customProperty("savonia/service_id", "") == GRID_ID)
                grid_id = grid.id()
                self.assertEqual(forest.children()[-1].layerId(), grid_id)
                self.assertTrue(grid.hasScaleBasedVisibility())
                self.assertTrue(grid.isInScaleRange(200))
                self.assertTrue(grid.isInScaleRange(300))
                self.assertFalse(grid.isInScaleRange(300.001))
                self.assertFalse(grid.isInScaleRange(500))
                # User layers survive grouping and group reorder, with check states.
                user = QgsVectorLayer("Polygon?crs=EPSG:3067", "user reference", "memory")
                project.addMapLayer(user, False)
                references.addLayer(user).setItemVisibilityChecked(False)
                forest.children()[0].setItemVisibilityChecked(False)
                # Also exercise restoring the managed group order after a user
                # adds another group above it; all existing children must survive.
                project.layerTreeRoot().insertGroup(0, "user group")
                for language in ("fi", "en", "fi"):
                    grid.renderer().symbol().symbolLayer(0).setBrushStyle(Qt.BrushStyle.SolidPattern)
                    grid.renderer().symbol().symbolLayer(0).setStrokeColor(QColor("red"))
                    # Repeated setup restores limits on reused layers too.
                    for layer in project.mapLayers().values():
                        if layer.customProperty("savonia/service_id", "") in (
                                "forest_centre_stand", "forest_centre_habitat"):
                            layer.setScaleBasedVisibility(False)
                            layer.setMinimumScale(500000)
                            layer.setMaximumScale(2000)
                    result = setup_project(project, language)
                    QgsApplication.processEvents()
                    QgsApplication.processEvents()
                    references = project.layerTreeRoot().findGroup(tr(language, "references_group"))
                    self.assertTrue(result["ready"], result["sources"])
                    self.assert_forest_visibility(project)
                    self.assert_grid_style(project)
                    self.assertEqual([node.name() for node in references.children()[:4]],
                                     [tr(language, key) for key, _ids in expected])
                    for group, (_key, ids) in zip(references.children(), expected):
                        self.assertEqual([node.layer().customProperty("savonia/service_id")
                                          for node in group.children()], list(ids))
                    self.assertEqual(references.children()[4].layerId(), user.id())
                    self.assertFalse(references.children()[4].itemVisibilityChecked())
                    self.assertFalse(references.children()[1].children()[0].itemVisibilityChecked())
                    self.assertEqual(set(project.mapLayers()), original_ids | {user.id()})
                    protected = [node.layer() for node in references.children()[2].children()]
                    symbols = [layer.renderer().symbol().symbolLayer(0) for layer in protected]
                    groundwater = references.children()[3].children()[0].layer().renderer().symbol().symbolLayer(0)
                    self.assertTrue(all(symbol.color() == symbols[0].color() for symbol in symbols))
                    for symbol in symbols:
                        self.assertEqual(symbol.color().alpha(), groundwater.color().alpha())
                        self.assertEqual(symbol.strokeColor().alpha(), groundwater.strokeColor().alpha())
                        self.assertEqual(symbol.strokeWidth(), groundwater.strokeWidth())
                    self.assertEqual(grid.name(), tr(language, "gridcell_layer"))
                    self.assertEqual(sum(layer.customProperty("savonia/service_id", "") == GRID_ID
                                         for layer in project.mapLayers().values()), 1)
                # A setup rerun restores the three layers absent in the reported UI.
                missing = {"forest_centre_habitat", "syke_nature_conservation_programme_areas",
                           "syke_protected_areas_wilderness"}
                project.removeMapLayers([layer.id() for layer in project.mapLayers().values()
                                         if layer.customProperty("savonia/service_id", "") in missing])
                restored = setup_project(project, "fi")
                QgsApplication.processEvents()
                QgsApplication.processEvents()
                self.assertTrue(restored["ready"], restored["sources"])
                self.assert_forest_visibility(project)
                self.assertEqual({layer.customProperty("savonia/service_id", "")
                                  for layer in project.mapLayers().values()} - {""},
                                 set(SERVICE_DEFINITIONS) | {"mml_parcels", "mml_property_identifiers"})
                self.assertEqual(len(project.layerTreeRoot().findLayers()), len(project.mapLayers()))
                with tempfile.TemporaryDirectory() as folder:
                    filename = str(Path(folder) / "forest.qgs")
                    self.assertTrue(project.write(filename))
                    reopened = QgsProject()
                    try:
                        self.assertTrue(reopened.read(filename))
                        self.assert_forest_visibility(reopened)
                        self.assert_grid_style(reopened)
                    finally:
                        reopened.clear()
        project.clear()

    def test_processing_exposes_required_polygon_grid_parameter_in_both_languages(self):
        for language in ("en", "fi"):
            with patch.object(QgsApplication, "locale", return_value=language):
                algorithm = ResponsibleForestPlanningInputsAlgorithm()
                algorithm.initAlgorithm()
                parameter = algorithm.parameterDefinition("GRIDCELLS")
                self.assertIsNotNone(parameter)
                self.assertEqual(parameter.description(), tr(language, "gridcell_layer"))
                self.assertFalse(parameter.flags() & Qgis.ProcessingParameterFlag.Optional)
                grid = QgsVectorLayer("Polygon?crs=EPSG:3067", "grid", "memory")
                self.assertTrue(parameter.checkValueIsAcceptable(grid))
                self.assertEqual(parameter.dataTypes(), [QgsProcessing.TypeVectorPolygon])


if __name__ == "__main__":
    unittest.main()
