"""Reusable local source records and Processing scenarios; no test discovery."""

from contextlib import contextmanager
import tempfile
from unittest.mock import patch

from qgis.core import (QgsFeature, QgsFeatureRequest, QgsGeometry, QgsProcessingContext, QgsProcessingFeedback,
                       QgsProject, QgsVectorLayer)
from savonia_responsible_forest_planning_tool.adapters.sources import SERVICE_DEFINITIONS, qgis_wfs_uri
from savonia_responsible_forest_planning_tool.processing.provider import ResponsibleForestPlanningInputsAlgorithm
from wfs_fixture import LocalWfs

def fixture_sources():
    return {
        "forest_centre_stand": {
            "standid": "stand-1", "VOLUME": 200.0, "SAWLOGVOLUME": 100.0,
            "VolumeGrowth": 4.0, "MeanAge": 40.0, "BasalArea": 20.0, "ProportionPine": 30.0,
        },
        "forest_centre_habitat": {"HabitatId": "habitat-1", "HabitatType": "3"},
        "syke_protected_areas_state_owned": {"kohdeid": "state-1", "OLOTILA": "Voimassa", "TYYPPILYHENNE": "VSA"},
        "syke_protected_areas_private_land": {"kohdeid": "private-1", "Olotila": "Voimassa", "KohdeTyyppi": "YSA"},
        "syke_protected_areas_wilderness": {"kohdeid": "wild-1", "olotila": "Voimassa", "kohdetyyppi": "EMA"},
        "syke_nature_conservation_programme_areas": {"LsoAlueTunnus": "programme-1", "Luokka": "AMO", "Subtype": "original"},
        "syke_groundwater_areas": {"tunnus": "groundwater-1", "alueluokka": "unfiltered"},
        "syke_rantaviiva_line_river": {"objectid": "line-1"},
        "syke_rantaviiva_polygon_river": {"objectid": "river-1"},
        "syke_rantaviiva_lake": {"objectid": "lake-1"},
        "forest_centre_gridcell": {"GRIDCELLID": "cell-1", "VOLUME": 250.0,
            "VOLUMEPINE": 70.0, "VOLUMESPRUCE": 130.0, "VOLUMEDECIDUOUS": 50.0,
            "AGE": 19.0, "SOILTYPE": 60, "DRAINAGESTATE": 6,
            "TREEDATADATE": "2021-06-01", "UPDATETIME": "2026-10-01"},
    }


def coordinates(x, y, width, height):
    return "{0},{1} {2},{1} {2},{3} {0},{3} {0},{1}".format(x, y, x + width, y + height)


def source_record(attributes, x=350000, y=6900000, width=100, height=100):
    return {"attributes": attributes, "coordinates": coordinates(x, y, width, height)}


class WorkflowFixtureMixin:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.temp.cleanup)

    @contextmanager
    def scenario(self, grid, stands=None, aoi=None, prime=False, version="1.0.0", page_size=0):
        schemas = fixture_sources()
        records = {source: [] for source in schemas}
        records["forest_centre_gridcell"] = grid
        records["forest_centre_stand"] = stands if stands is not None else [source_record(schemas["forest_centre_stand"])]
        with LocalWfs(schemas, records=records, version=version, page_size=page_size,
                      geometry_types={"syke_rantaviiva_line_river": "LineString"}) as fixture:
            definitions = {source: {**definition, "endpoint": fixture.endpoint}
                           for source, definition in SERVICE_DEFINITIONS.items()}
            with patch.dict(SERVICE_DEFINITIONS, definitions):
                aoi_layer = QgsVectorLayer("Polygon?crs=EPSG:3067", "AOI", "memory")
                for text in aoi or [coordinates(350000, 6900000, 100, 100)]:
                    feature = QgsFeature()
                    feature.setGeometry(QgsGeometry.fromWkt("POLYGON ((" + text.replace(" ", ";").replace(",", " ").replace(";", ",") + "))"))
                    self.assertTrue(aoi_layer.dataProvider().addFeatures([feature])[0])
                aoi_layer.updateExtents()
                layers = {}
                for source in definitions:
                    typename = "fixture:" + source
                    uri = "url='{0}' typename='{1}' version='1.0.0' restrictToRequestBBOX='1'".format(fixture.endpoint, typename)
                    if version == "2.0.0":
                        uri = qgis_wfs_uri({"endpoint": fixture.endpoint, "feature_type": typename})
                    layer = QgsVectorLayer(uri, source, "WFS")
                    self.assertTrue(layer.isValid(), layer.error().message())
                    layer.setCustomProperty("savonia/endpoint", fixture.endpoint)
                    layer.setCustomProperty("savonia/feature_type", typename)
                    layer.setCustomProperty("savonia/schema_json", "obsolete saved schema")
                    if prime:
                        # Even zero-result initialization can start a download.
                        request = QgsFeatureRequest().setFilterFids([]).setFilterRect(aoi_layer.extent()).setLimit(0)
                        iterator = layer.getFeatures(request)
                        iterator.close()
                    layers[source] = layer
                yield fixture, layers, aoi_layer

    def run_algorithm(self, layers, aoi, language, name, feedback=None, selected_only=False, sawlog_price=75.25):
        algorithm = ResponsibleForestPlanningInputsAlgorithm()
        algorithm.initAlgorithm()
        parameters = {algorithm.AOI: aoi, algorithm.OUTPUT_FOLDER: self.temp.name,
                      algorithm.OUTPUT_NAME: name, algorithm.SELECTED_ONLY: selected_only,
                      "SAWLOG_PRICE_EUR_M3": sawlog_price}
        for parameter, source in {
            algorithm.STANDS: "forest_centre_stand", algorithm.GRIDCELLS: "forest_centre_gridcell",
            algorithm.HABITATS: "forest_centre_habitat", algorithm.PROTECTED: "syke_protected_areas_state_owned",
            algorithm.PROTECTED_PRIVATE: "syke_protected_areas_private_land",
            algorithm.PROTECTED_WILDERNESS: "syke_protected_areas_wilderness",
            algorithm.PROGRAMME: "syke_nature_conservation_programme_areas",
            algorithm.GROUNDWATER: "syke_groundwater_areas",
            algorithm.LINE_RIVER: "syke_rantaviiva_line_river",
            algorithm.POLYGON_RIVER: "syke_rantaviiva_polygon_river",
            algorithm.LAKE: "syke_rantaviiva_lake",
        }.items():
            parameters[parameter] = layers[source]
        context = QgsProcessingContext()
        context.setProject(QgsProject.instance())
        with patch("savonia_responsible_forest_planning_tool.processing.provider.selected_language", return_value=language):
            return algorithm.processAlgorithm(parameters, context, feedback or QgsProcessingFeedback())

