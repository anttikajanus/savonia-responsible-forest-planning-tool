"""Exact local grid intersections, independent of canvas rendering and scale."""

import math

from qgis.core import Qgis, QgsFeature, QgsGeometry, QgsProcessingException, QgsSpatialIndex, QgsWkbTypes

from ...i18n import tr
from .common import _check_cancelled


AREA_TOLERANCE_M2 = 1e-8


def _translated_geometry(geometry, origin, language, source_id):
    local = QgsGeometry(geometry)
    if local.translate(-origin.x(), -origin.y()) != Qgis.GeometryOperationResult.Success:
        raise QgsProcessingException(tr(language, "error_grid_overlay", source_id=source_id))
    return local


def projected_area_m2(geometry, language="en"):
    """Measure a projected polygon near the origin, retaining its metre units."""
    return _translated_geometry(geometry, geometry.boundingBox().center(),
                                language, "reporting_geometry").area()


def deduplicate_grid_records(records, language="en", feedback=None):
    """Keep identical repeated IDs once, retaining original-geometry provenance.

    Return unique records and their original positions so the clipped snapshot
    retains precisely the same records. Attribute or original geometry changes
    for one ID are conflicting source versions, even if the AOI clips them alike.
    """
    _check_cancelled(feedback, language)
    by_id = {}
    unique = []
    positions = []
    for position, record in enumerate(records):
        _check_cancelled(feedback, language)
        source_id = record["source_id"]
        if source_id in by_id:
            previous = by_id[source_id]
            same_geometry = (
                previous["source_geometry_wkb"] == record["source_geometry_wkb"]
                if "source_geometry_wkb" in previous and "source_geometry_wkb" in record
                else previous["geometry"].isGeosEqual(record["geometry"])
            )
            if not same_geometry or previous["attributes"] != record["attributes"]:
                raise QgsProcessingException(tr(language, "error_grid_conflicting_id", source_id=source_id))
            continue
        by_id[source_id] = record
        unique.append(record)
        positions.append(position)
    return unique, positions


def partition_index(records, service_id, language="en", feedback=None, *,
                    overlap_tolerance_m2=AREA_TOLERANCE_M2, overlap_callback=None):
    """Validate/index polygons, rejecting overlaps unless the caller records them."""
    _check_cancelled(feedback, language)
    spatial_index = QgsSpatialIndex()
    for index, record in enumerate(records):
        _check_cancelled(feedback, language)
        geometry = record["geometry"]
        if (geometry.isNull() or geometry.isEmpty() or not geometry.isGeosValid()
                or QgsWkbTypes.geometryType(geometry.wkbType()) != QgsWkbTypes.PolygonGeometry
                or not math.isfinite(geometry.area()) or geometry.area() <= AREA_TOLERANCE_M2):
            raise QgsProcessingException(tr(language, "source_feature_geometry_invalid",
                                            source=service_id, feature_id=record["source_id"]))
        for candidate in spatial_index.intersects(geometry.boundingBox()):
            _check_cancelled(feedback, language)
            other = records[candidate]
            intersection = geometry.intersection(other["geometry"])
            if intersection.isNull() or (not intersection.isEmpty() and not intersection.isGeosValid()):
                raise QgsProcessingException(tr(language, "error_partition_overlay", source=service_id,
                                                first=other["source_id"], second=record["source_id"]))
            if not intersection.isEmpty() and intersection.area() > overlap_tolerance_m2:
                if overlap_callback is None:
                    raise QgsProcessingException(tr(language, "error_source_partition_overlap", source=service_id,
                                                    first=other["source_id"], second=record["source_id"]))
                overlap_callback(other, record, projected_area_m2(intersection, language))
        feature = QgsFeature()
        feature.setId(index)
        feature.setGeometry(geometry)
        if not spatial_index.addFeature(feature):
            raise QgsProcessingException(tr(language, "error_partition_index", source=service_id))
    return spatial_index


class GridCellSampler:
    """Reuse one clipped EPSG:3067 source snapshot and its local spatial index."""

    def __init__(self, records, language="en", feedback=None):
        original = list(records)
        self.records, self.kept_positions = deduplicate_grid_records(original, language, feedback)
        self.duplicate_count = len(original) - len(self.records)
        self.language = language
        self.feedback = feedback
        self.index = partition_index(self.records, "forest_centre_gridcell", language, feedback)

    def sample(self, geometry):
        """Return only positive-area intersections in hectares for the pure core."""
        _check_cancelled(self.feedback, self.language)
        # EPSG:3067 northings are millions of metres. Overlay vertices rounded at
        # that magnitude can make disjoint intersection areas exceed the parent
        # by more than the storage tolerance. Translate copies for the overlay;
        # this is an isometry in the same projected metre units, not a CRS change.
        origin = geometry.boundingBox().center()
        local_geometry = _translated_geometry(geometry, origin, self.language, "reporting_geometry")
        parts = []
        for index in sorted(self.index.intersects(geometry.boundingBox())):
            _check_cancelled(self.feedback, self.language)
            record = self.records[index]
            local_cell = _translated_geometry(record["geometry"], origin, self.language, record["source_id"])
            intersection = local_geometry.intersection(local_cell)
            if intersection.isNull() or (not intersection.isEmpty() and not intersection.isGeosValid()):
                raise QgsProcessingException(tr(self.language, "error_grid_overlay",
                                                source_id=record["source_id"]))
            if not intersection.isEmpty() and intersection.area() > AREA_TOLERANCE_M2:
                parts.append({"area_ha": intersection.area() / 10000,
                              "values": record["values"], "source_id": record["source_id"]})
        if parts:
            reporting_area_ha = local_geometry.area() / 10000
            sampled_area_ha = math.fsum(part["area_ha"] for part in parts)
            difference_m2 = (reporting_area_ha - sampled_area_ha) * 10000
            # The retrieved cells were already clipped in source/global
            # coordinates. Their boundary vertices retain that coordinate ULP.
            # Area uncertainty is bounded by coordinate spacing times polygon
            # perimeter (8 ULPs allows the two overlay boundaries). This is
            # separate from the unchanged geometry/overlap storage threshold.
            bounds = geometry.boundingBox()
            coordinate_spacing = math.ulp(max(1.0, abs(bounds.xMinimum()), abs(bounds.xMaximum()),
                                              abs(bounds.yMinimum()), abs(bounds.yMaximum())))
            roundoff_m2 = max(AREA_TOLERANCE_M2, 8 * coordinate_spacing * local_geometry.length())
            if AREA_TOLERANCE_M2 < abs(difference_m2) <= roundoff_m2:
                # Reconcile only a numerical closure discrepancy. Real partial
                # coverage remains partial; all adjusted areas retain their
                # relative weights without producing separate diagnostic records.
                factor = reporting_area_ha / sampled_area_ha
                for part in parts:
                    part["area_ha"] *= factor
        return parts
