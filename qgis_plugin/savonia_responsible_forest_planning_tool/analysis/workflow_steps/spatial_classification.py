"""Perform spatial overlays and assemble classified stand results."""

import logging
import math

from qgis.core import QgsGeometry, QgsProcessingException

from ..classification import assemble_classified_piece, interpret_sources
from ...i18n import tr
from ...adapters.classified_result import create_classified_result_layer
from ...app_logging import LOGGER_NAME
from .common import _check_cancelled, _feedback
from .grid_sampling import GridCellSampler, partition_index, projected_area_m2

_MINIMUM_CRITERION_OVERLAP_AREA_M2 = 1.0
_MINIMUM_OUTPUT_PIECE_AREA_M2 = 1e-8

logger = logging.getLogger(LOGGER_NAME + ".analysis.spatial_classification")


def _stand_overlaps(stand_features, inputs, feedback):
    """Inspect each clipped stand pair once, retaining all source geometries."""
    affected = set()
    source_ids = set()
    pair_count = 0
    run_id = inputs.get("run_id", "unknown")

    def record_overlap(first, second, area_m2):
        nonlocal pair_count
        pair_count += 1
        affected.update((id(first), id(second)))
        source_ids.update((str(first["source_id"]), str(second["source_id"])))
        logger.debug(
            "run_id=%s stage=spatial_classification source=forest_centre_stand "
            "event=stand_overlap_pair first=%s second=%s overlap_area_m2=%.17g",
            run_id, first["source_id"], second["source_id"], area_m2,
        )

    partition_index(stand_features, "forest_centre_stand", inputs["language"], feedback,
                    overlap_callback=record_overlap)
    summary = {"pair_count": pair_count, "affected_stand_count": len(affected),
               "stand_id_sample": sorted(source_ids)[:20]}
    if pair_count:
        logger.warning(
            "run_id=%s stage=spatial_classification source=forest_centre_stand "
            "event=stand_overlaps pair_count=%d affected_stand_count=%d stand_id_sample=%s",
            run_id, pair_count, len(affected), summary["stand_id_sample"],
        )
    return affected, summary


def _has_criterion_overlap_above_threshold(geometry, candidate):
    """Return whether polygon overlap exceeds the shared criterion hit threshold."""
    intersection = geometry.intersection(candidate)
    if intersection.isNull():
        raise RuntimeError("QGIS returned a null geometry during overlap check.")
    return not intersection.isEmpty() and intersection.area() > _MINIMUM_CRITERION_OVERLAP_AREA_M2


def _attach_classification_diagnostics(coverage, diagnostics):
    for row in coverage:
        detail = diagnostics.get(row["service_id"], {})
        for key, value in detail.items():
            if key != "reason_code":
                row[key] = value

def _split_geometry(geometry, boundary):
    """Split a polygon at an overlay boundary, preserving positive-area pieces."""
    try:
        intersection = geometry.intersection(boundary)
        difference = geometry.difference(boundary)
    except Exception as exc:
        raise RuntimeError(str(exc))
    if intersection.isNull() or difference.isNull():
        raise RuntimeError("QGIS returned a null geometry during criterion overlay.")
    # A criterion hit requires more than 1 m² of overlap. Retain smaller output
    # fragments when splitting a qualifying overlap using the separate geometry
    # storage tolerance below.
    if intersection.isEmpty() or intersection.area() <= _MINIMUM_CRITERION_OVERLAP_AREA_M2:
        return [(geometry, False)]
    pieces = [(intersection, True)]
    if not difference.isEmpty() and difference.area() > _MINIMUM_OUTPUT_PIECE_AREA_M2:
        pieces.append((difference, False))
    return pieces

def _polygon_parts(geometry):
    if geometry.isEmpty():
        return []
    if geometry.isMultipart():
        # Keep disconnected pieces as separate rows for traceable area and source attribution.
        return [QgsGeometry(part) for part in geometry.asGeometryCollection() if not part.isEmpty() and part.area() > _MINIMUM_OUTPUT_PIECE_AREA_M2]
    return [geometry]

def _split_stand(stand_geometry, criteria, language):
    pieces = [(stand_geometry, set(), {})]
    for criterion in criteria:
        next_pieces = []
        for geometry, matched, source_ids in pieces:
            try:
                split_parts = _split_geometry(geometry, criterion["geometry"])
            except Exception as exc:
                raise QgsProcessingException(
                    tr(language, "error_criterion_overlay", criterion=criterion["criterion"],
                       source_id=criterion["source_id"], detail=exc)
                )
            for part, inside in split_parts:
                new_matched = set(matched)
                # Each branch owns its ID sets; adding a later overlapping
                # record must not change the provenance of sibling pieces.
                new_sources = {key: set(identifiers) for key, identifiers in source_ids.items()}
                if inside:
                    new_matched.add(criterion["criterion"])
                    new_sources.setdefault(criterion["criterion"], set()).add(criterion["source_id"])
                next_pieces.extend((polygon, new_matched, new_sources) for polygon in _polygon_parts(part))
        pieces = next_pieces
    return pieces

def classify_source_features(inputs, retrieved, feedback=None):
    """Apply source interpretation and spatial rules to retrieved features."""
    language = inputs["language"]
    progress_message = tr(language, "progress_classify")
    _feedback(feedback, "setProgressText", progress_message)
    _feedback(feedback, "pushInfo", progress_message)
    source_features = retrieved["source_features"]
    source_display_names = inputs["source_display_names"]
    coverage = [dict(row) for row in retrieved["coverage"]]
    criteria, source_states, classification_diagnostics = interpret_sources(
        source_features,
        {row["service_id"]: row["status"] for row in coverage},
    )
    source_states["syke_protected_areas"] = retrieved["protected_areas_status"]
    unrecognized_sources = []
    for service_id, diagnostics in classification_diagnostics.items():
        if diagnostics.get("reason_code"):
            records = diagnostics.get("unrecognized_records", ())
            feature_ids = diagnostics.get("unrecognized_feature_ids", ())
            if records:
                feature_ids = [record.get("source_id", "") for record in records]
            feature_summary = ", ".join(str(value) for value in feature_ids[:10])
            if len(feature_ids) > 10:
                feature_summary += ", ..."
            unrecognized_sources.append((
                source_display_names.get(service_id, service_id),
                tr(language, "source_invalid_values", features=feature_summary or "unknown"),
            ))
    if unrecognized_sources:
        details = "\n".join(
            "{0}: {1}".format(source_name, message)
            for source_name, message in unrecognized_sources
        )
        raise QgsProcessingException(tr(language, "error_sources_invalid", details=details))
    _attach_classification_diagnostics(coverage, classification_diagnostics)
    stand_coverage = next((row for row in coverage if row["service_id"] == "forest_centre_stand"), {})
    source_states["forest_centre_stand"] = stand_coverage.get("status", "NOT_AVAILABLE")

    # Reuse the clipped retrieval snapshot so classification cannot trigger a
    # second WFS request that may return the full remote layer.
    stand_features = source_features["forest_centre_stand"]
    overlapping_stands, overlap_summary = _stand_overlaps(stand_features, inputs, feedback)
    grid_sampler = retrieved.get("grid_sampler")
    if grid_sampler is None:
        grid_sampler = GridCellSampler(source_features.get("forest_centre_gridcell", ()), language, feedback)
    result_rows = []
    stand_count = max(len(stand_features), 1)
    for index, stand_record in enumerate(stand_features):
        _check_cancelled(feedback, language)
        _feedback(feedback, "setProgress", 70 + int(20 * index / stand_count))
        if index % 100 == 0:
            _feedback(feedback, "setProgressText", tr(
                language, "progress_classify_items", count=index, total=len(stand_features),
            ))
        if index and index % 500 == 0:
            _feedback(feedback, "pushInfo", tr(
                language, "progress_classify_items", count=index, total=len(stand_features),
            ))
        clipped = QgsGeometry(stand_record["geometry"])
        stand_id = stand_record["source_id"]
        if clipped.isNull() or clipped.isEmpty() or not clipped.isGeosValid():
            raise QgsProcessingException(tr(
                language, "source_feature_geometry_invalid",
                source=source_display_names["forest_centre_stand"], feature_id=stand_id,
            ))
        try:
            stand_criteria = [c for c in criteria if clipped.intersects(c["geometry"])]
            # Boundary contact is not a Section 10 hit. Only positive-area
            # overlap promotes all pieces derived from this original stand.
            section10_hits = [
                c for c in stand_criteria
                if c["criterion"] == "section10"
                and _has_criterion_overlap_above_threshold(clipped, c["geometry"])
            ]
        except Exception as exc:
            raise QgsProcessingException(tr(language, "error_geometry_overlay", detail=exc))
        # Section 10 promotion is stand-wide, so any positive-area overlap marks
        # every split piece even when a piece itself lies outside the habitat.
        for piece, matched, source_ids in _split_stand(clipped, stand_criteria, language):
            if section10_hits:
                matched.add("section10")
                source_ids.setdefault("section10", set()).update(c["source_id"] for c in section10_hits)
            piece_programme_ids = source_ids.get("programme", set())
            programme_info = []
            for criterion in stand_criteria:
                if criterion["criterion"] != "programme" or criterion["source_id"] not in piece_programme_ids:
                    continue
                attrs = criterion.get("attributes", {})
                actual_names = {name.lower(): name for name in attrs}
                programme_info.append({
                    key: attrs.get(actual_names[key.lower()])
                    for key in ("LsoAlueTunnus", "Luokka", "Subtype", "Nimi", "MuutosPvm", "Lisatieto")
                    if key.lower() in actual_names
                })
            if piece_programme_ids:
                try:
                    protected_intersection = any(
                        criterion["criterion"] == "protected"
                        and _has_criterion_overlap_above_threshold(piece, criterion["geometry"])
                        for criterion in criteria
                    )
                except Exception as exc:
                    raise QgsProcessingException(tr(language, "error_geometry_overlay", detail=exc))
                # Missing protected-area coverage cannot establish that this
                # programme polygon has no protected-area overlap.
                overlap_value = (
                    "YES" if protected_intersection
                    else "UNKNOWN" if source_states.get("syke_protected_areas") != "AVAILABLE"
                    else "NO"
                )
            else:
                overlap_value = None
            evidence = {
                "active_protected": "protected" in matched,
                "section10": bool(section10_hits),
                "programme_area": "programme" in matched,
                "groundwater_area": "groundwater" in matched,
                "other_valuable_habitat": "other_habitat" in matched,
                "source_ids": source_ids,
                "section10_stand_promoted": (
                    True if section10_hits else False
                    if source_states.get("forest_centre_habitat") == "AVAILABLE" else None
                ),
                "programme_info": programme_info,
                "programme_protected_overlap": overlap_value,
            }
            reporting_area_m2 = projected_area_m2(piece, language)
            intersections = grid_sampler.sample(piece)
            try:
                result_row = assemble_classified_piece(
                    stand_id, stand_record["attributes"], reporting_area_m2 / 10000.0,
                    evidence, source_states, grid_intersections=intersections,
                )
            except ValueError as exc:
                intersected_area_m2 = math.fsum(item["area_ha"] for item in intersections) * 10000
                logger.error(
                    "run_id=%s stage=spatial_classification event=grid_indicator_area_invariant_failed "
                    "stand_id=%s reporting_area_m2=%.17g intersected_area_m2=%.17g "
                    "excess_area_m2=%.17g intersection_count=%d reason=%s",
                    inputs.get("run_id", "unknown"), stand_id, reporting_area_m2, intersected_area_m2,
                    intersected_area_m2 - reporting_area_m2, len(intersections), exc,
                )
                raise QgsProcessingException(tr(language, "error_grid_statistics", stand_id=stand_id, detail=exc)) from exc
            result_row["geometry"] = piece
            result_row["stand_has_overlap"] = id(stand_record) in overlapping_stands
            result_rows.append(result_row)
    if not result_rows:
        raise QgsProcessingException(tr(language, "error_no_stands"))

    _feedback(feedback, "setProgress", 90)

    output_layer = create_classified_result_layer(result_rows, language)
    return {
        "result_rows": result_rows,
        "output_layer": output_layer,
        "coverage": coverage,
        "stand_overlap_summary": overlap_summary,
    }


