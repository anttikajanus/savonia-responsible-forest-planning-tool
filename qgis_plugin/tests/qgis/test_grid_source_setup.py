"""Grid readiness and project setup against a tiny local WFS and QGIS runtime."""

import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.environ.get(
    "RESPONSIBLE_FOREST_PLANNING_TEST_PLUGIN_ROOT",
    os.environ.get("SAVONIA_TEST_PLUGIN_ROOT", str(Path(__file__).resolve().parents[2])),
))

from qgis.core import Qgis, QgsApplication, QgsProcessing, QgsProject, QgsVectorLayer

APP = QgsApplication.instance()
if APP is None:
    APP = QgsApplication([], False)
    APP.initQgis()

from savonia_responsible_forest_planning_tool.adapters.source_layers import (
    source_identifier_field, verify_source_layer,
)
from savonia_responsible_forest_planning_tool.adapters.sources import SERVICE_DEFINITIONS
from savonia_responsible_forest_planning_tool.analysis.worker_task import capture_worker_inputs
from savonia_responsible_forest_planning_tool.adapters.project_setup import setup_project
from savonia_responsible_forest_planning_tool.i18n import tr
from savonia_responsible_forest_planning_tool.processing.provider import ResponsibleForestPlanningInputsAlgorithm
from wfs_fixture import LocalWfs


GRID_ID = "forest_centre_gridcell"
GRID_FIELDS = {
    "GridCellId": "cell-1", "VOLUME": 250.0, "VolumePine": 100.0,
    "VolumeSpruce": 80.0, "VolumeDeciduous": 70.0, "Age": 40.0,
    "SoilType": 60, "DrainageState": 6,
}


class GridSourceTest(unittest.TestCase):
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
        with LocalWfs(sources) as fixture:
            definitions = {
                source: {**definition, "endpoint": fixture.endpoint, "feature_type": "fixture:" + source}
                for source, definition in SERVICE_DEFINITIONS.items()
            }
            with patch.dict(SERVICE_DEFINITIONS, definitions):
                first = setup_project(project, "en")
                self.assertTrue(first["ready"], first["sources"])
                references = project.layerTreeRoot().findGroup(tr("en", "references_group"))
                grid = next(layer for layer in project.mapLayers().values()
                            if layer.customProperty("savonia/service_id", "") == GRID_ID)
                grid_id = grid.id()
                self.assertEqual(references.children()[-1].layerId(), grid_id)
                self.assertTrue(grid.hasScaleBasedVisibility())
                self.assertTrue(grid.isInScaleRange(200))
                self.assertTrue(grid.isInScaleRange(300))
                self.assertFalse(grid.isInScaleRange(300.001))
                self.assertFalse(grid.isInScaleRange(500))
                # A user layer appended after setup must retain its position
                # relative to the other references when the grid moves below it.
                user = QgsVectorLayer("Polygon?crs=EPSG:3067", "user reference", "memory")
                project.addMapLayer(user, False)
                user_node = references.addLayer(user)
                other_ids = [node.layerId() for node in references.children() if node.layerId() != grid_id]
                # Also exercise restoring the managed group order after a user
                # adds another group above it; all existing children must survive.
                project.layerTreeRoot().insertGroup(0, "user group")
                for language in ("fi", "en", "fi"):
                    result = setup_project(project, language)
                    references = project.layerTreeRoot().findGroup(tr(language, "references_group"))
                    self.assertTrue(result["ready"], result["sources"])
                    self.assertEqual(references.children()[-1].layerId(), grid_id)
                    self.assertEqual([node.layerId() for node in references.children()[:-1]], other_ids,
                                     [node.name() for node in references.children()])
                    self.assertEqual(grid.name(), tr(language, "gridcell_layer"))
                    self.assertEqual(sum(layer.customProperty("savonia/service_id", "") == GRID_ID
                                         for layer in project.mapLayers().values()), 1)
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
