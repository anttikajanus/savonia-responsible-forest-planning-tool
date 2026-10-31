"""Required Ranta10 source contracts and managed reference-map behavior."""

import unittest
import tempfile
from unittest.mock import patch

from qgis_test_environment import qgis_application

APP = qgis_application()

from qgis.core import Qgis, QgsApplication, QgsProject, QgsVectorLayer
from qgis.PyQt.QtGui import QColor

from savonia_responsible_forest_planning_tool.adapters.project_setup import setup_project
from savonia_responsible_forest_planning_tool.adapters.source_layers import verify_source_layer
from savonia_responsible_forest_planning_tool.adapters.sources import SERVICE_DEFINITIONS
from savonia_responsible_forest_planning_tool.analysis.source_readiness import assess_source_schema
from savonia_responsible_forest_planning_tool.i18n import tr
from wfs_fixture import LocalWfs
from oapif_fixture import LocalOapif
from wmts_fixture import LocalWmts


WATER_SOURCES = (
    "syke_rantaviiva_line_river",
    "syke_rantaviiva_polygon_river",
    "syke_rantaviiva_lake",
)


class WaterSourceContractTest(unittest.TestCase):
    def test_three_required_products_have_stable_wfs_and_geometry_contracts(self):
        self.assertEqual(len(WATER_SOURCES), 3)
        for service_id in WATER_SOURCES:
            with self.subTest(service_id=service_id):
                definition = SERVICE_DEFINITIONS[service_id]
                self.assertTrue(definition["required"])
                self.assertEqual(
                    definition["endpoint"],
                    "https://paikkatiedot.ymparisto.fi/geoserver/syke_rantaviiva/wfs",
                )
                self.assertEqual(definition["geometry"],
                                 "line" if service_id == WATER_SOURCES[0] else "polygon")
                self.assertTrue(definition["feature_type"].startswith("syke_rantaviiva:"))
                self.assertEqual(assess_source_schema(service_id, ["OBJECTID"])["status"], "AVAILABLE")
                self.assertEqual(assess_source_schema(service_id, [])["reason_code"], "REQUIRED_FIELDS_MISSING")

    def test_water_source_readiness_checks_real_geometry_type(self):
        for geometry, valid in (("LineString", True), ("Polygon", False)):
            with self.subTest(geometry=geometry):
                with LocalWfs(
                    {"water": {"objectid": "water-1"}},
                    geometry_types={"water": geometry},
                ) as fixture:
                    definition = {
                        **SERVICE_DEFINITIONS[WATER_SOURCES[0]],
                        "endpoint": fixture.endpoint,
                        "feature_type": "fixture:water",
                    }
                    with patch.dict(SERVICE_DEFINITIONS, {WATER_SOURCES[0]: definition}):
                        layer = QgsVectorLayer(
                            "url='{0}' typename='fixture:water' version='1.0.0'".format(fixture.endpoint),
                            "water", "WFS",
                        )
                        self.assertTrue(layer.isValid(), layer.error().message())
                        layer.setCustomProperty("savonia/endpoint", fixture.endpoint)
                        layer.setCustomProperty("savonia/feature_type", "fixture:water")
                        metadata, error = verify_source_layer(layer, WATER_SOURCES[0], "en")
                        self.assertEqual(error is None, valid)
                        if valid:
                            self.assertEqual(metadata["service_id"], WATER_SOURCES[0])
                        else:
                            self.assertEqual(error["reason_code"], "SOURCE_GEOMETRY_TYPE_INVALID")

    def test_setup_orders_reuses_styles_and_restores_water_visibility_in_both_languages(self):
        sources = {
            "forest_centre_stand": {"volume": 200., "sawlogvolume": 100., "volumegrowth": 4., "meanage": 40.},
            "forest_centre_habitat": {"habitattype": "3"},
            "syke_protected_areas_state_owned": {"olotila": "Voimassa", "tyyppilyhenne": "VSA"},
            "syke_protected_areas_private_land": {"olotila": "Voimassa", "kohdetyyppi": "YSA"},
            "syke_protected_areas_wilderness": {"olotila": "Voimassa", "kohdetyyppi": "EMA"},
            "syke_nature_conservation_programme_areas": {"lsoaluetunnus": "programme-1", "luokka": "AMO"},
            "syke_groundwater_areas": {"tunnus": "groundwater-1"},
            "forest_centre_gridcell": {"gridcellid": "cell-1", "volume": 250., "volumepine": 70.,
                "volumespruce": 130., "volumedeciduous": 50., "age": 19., "soiltype": 60, "drainagestate": 6},
            WATER_SOURCES[0]: {"objectid": "line-1"},
            WATER_SOURCES[1]: {"objectid": "river-1"},
            WATER_SOURCES[2]: {"objectid": "lake-1"},
        }
        geometry_types = {WATER_SOURCES[0]: "LineString"}
        project = QgsProject()
        basemap = QgsVectorLayer("Polygon?crs=EPSG:3067", "basemap", "memory")
        basemap.setCustomProperty("savonia/layer_id", "osm_xyz")
        project.addMapLayer(basemap)
        with (LocalWfs(sources, geometry_types=geometry_types) as fixture,
              LocalOapif() as parcels, LocalWmts() as maps):
            definitions = {
                source: {**definition, "endpoint": fixture.endpoint, "feature_type": "fixture:" + source}
                for source, definition in SERVICE_DEFINITIONS.items()
            }
            with (patch.dict(SERVICE_DEFINITIONS, definitions),
                  patch("savonia_responsible_forest_planning_tool.adapters.sources.MML_WMTS_CAPABILITIES", maps.capabilities_url),
                  patch("savonia_responsible_forest_planning_tool.adapters.sources.mml_api_key", return_value=parcels.key),
                  patch("savonia_responsible_forest_planning_tool.adapters.project_setup.mml_api_key", return_value=parcels.key),
                  patch("savonia_responsible_forest_planning_tool.adapters.sources.MML_PARCEL_ENDPOINT", parcels.endpoint)):
                for language in ("en", "fi", "en"):
                    setup = setup_project(project, language)
                    QgsApplication.processEvents()
                    self.assertTrue(setup["ready"], setup["sources"])
                    references = project.layerTreeRoot().findGroup(tr(language, "references_group"))
                    water = references.children()[3]
                    self.assertEqual(water.name(), tr(language, "water_group"))
                    expected = ("syke_groundwater_areas",) + WATER_SOURCES
                    self.assertEqual(
                        [node.layer().customProperty("savonia/service_id") for node in water.children()],
                        list(expected),
                    )
                    for service_id, key in zip(WATER_SOURCES, ("line_river_layer", "polygon_river_layer", "lake_layer")):
                        layer = next(item for item in project.mapLayers().values()
                                     if item.customProperty("savonia/service_id", "") == service_id)
                        self.assertEqual(layer.name(), tr(language, key))
                        self.assertTrue(layer.hasScaleBasedVisibility())
                        self.assertEqual(layer.maximumScale(), 0.0)
                        self.assertTrue(layer.isInScaleRange(7763))
                        self.assertFalse(layer.isInScaleRange(7763.001))
                        symbol = layer.renderer().symbol()
                        color = symbol.symbolLayer(0).color() if service_id == WATER_SOURCES[0] else symbol.symbolLayer(0).fillColor()
                        self.assertEqual(color.getRgb()[:3], QColor("#4f9fe0").getRgb()[:3])
                    line = next(item for item in project.mapLayers().values()
                                if item.customProperty("savonia/service_id", "") == WATER_SOURCES[0])
                    self.assertEqual(line.geometryType(), Qgis.GeometryType.Line)
                    self.assertEqual(sum(item.customProperty("savonia/service_id", "") == WATER_SOURCES[0]
                                         for item in project.mapLayers().values()), 1)
                # Repeating setup restores managed presentation without
                # replacing layer identities.
                ids = {service_id: next(item.id() for item in project.mapLayers().values()
                                         if item.customProperty("savonia/service_id", "") == service_id)
                       for service_id in WATER_SOURCES}
                for service_id in WATER_SOURCES:
                    managed = project.mapLayer(ids[service_id])
                    managed.setScaleBasedVisibility(False)
                    managed.setMinimumScale(500000)
                    managed.renderer().symbol().symbolLayer(0).setColor(QColor("red"))
                self.assertTrue(setup_project(project, "en")["ready"])
                for service_id in WATER_SOURCES:
                    managed = project.mapLayer(ids[service_id])
                    self.assertTrue(managed.hasScaleBasedVisibility())
                    self.assertTrue(managed.isInScaleRange(7763))
                    self.assertFalse(managed.isInScaleRange(7763.001))
                    self.assertEqual(managed.renderer().symbol().symbolLayer(0).color().getRgb()[:3],
                                     QColor("#4f9fe0").getRgb()[:3])
                with tempfile.TemporaryDirectory() as folder:
                    filename = folder + "/water-setup.qgs"
                    self.assertTrue(project.write(filename))
                    reopened = QgsProject()
                    try:
                        self.assertTrue(reopened.read(filename))
                        for service_id in WATER_SOURCES:
                            saved = next(item for item in reopened.mapLayers().values()
                                         if item.customProperty("savonia/service_id", "") == service_id)
                            self.assertTrue(saved.hasScaleBasedVisibility())
                            self.assertTrue(saved.isInScaleRange(7763))
                            self.assertFalse(saved.isInScaleRange(7763.001))
                    finally:
                        reopened.clear()


if __name__ == "__main__":
    unittest.main()
