"""Retrieve, transform, clip, and snapshot source features."""

import datetime
import logging
import time
from urllib.parse import quote
from dataclasses import dataclass

from qgis.PyQt.QtCore import QCoreApplication, QEvent, QThread
from qgis.PyQt.QtXml import QDomDocument

from qgis.core import (
    Qgis, QgsCoordinateTransform, QgsExpression, QgsFeature, QgsFeatureRequest, QgsGeometry,
    QgsOgcUtils, QgsProcessingException, QgsVectorLayer, QgsWkbTypes,
)

from ...i18n import tr
from ...app_logging import LOGGER_NAME
from ...adapters.provider_utils import require_provider_success
from ...adapters.source_layers import source_identifier_field
from ...adapters.sources import safe_source_error
from ..source_readiness import PROTECTED_SOURCE_IDS, normalize_source_attributes
from .common import TARGET_CRS, _apply_coordinate_transform, _check_cancelled
from .grid_sampling import AREA_TOLERANCE_M2, GridCellSampler, deduplicate_grid_records


logger = logging.getLogger(LOGGER_NAME + ".analysis.source_loading")

# A filter-only GET budget, leaving room for endpoint, subset and paging options.
# This is our conservative request policy, not a claimed service URL limit.
MAX_ENCODED_POLYGON_FILTER_BYTES = 6000


def _polygon_request_expression(geometry, source_crs):
    """Return a pushable AOI expression, or a bounded-read fallback for large filters."""
    # QGIS emits GML 3.2 MultiPolygon for multipart WKT, which the Forest
    # Centre service rejects with a null-expression exception. Polygon
    # predicates joined with OR preserve the AOI, including each part's holes.
    parts = geometry.asGeometryCollection() if geometry.isMultipart() else [geometry]
    expression = " OR ".join(
        "intersects($geometry, geom_from_wkt({0}))".format(
            QgsExpression.quotedString(part.asWkt(17)),
        ) for part in parts
    )
    # QGIS 3.44 only pushes function/unary roots through its expression
    # serializer. Double negation preserves the OR predicate's meaning and
    # lets both supported baselines send the complete filter to the server.
    if len(parts) > 1:
        expression = "NOT (NOT ({0}))".format(expression)
    document = QDomDocument()
    element = QgsOgcUtils.expressionToOgcExpression(
        QgsExpression(expression), document, QgsOgcUtils.GML_3_2_1,
        QgsOgcUtils.FILTER_FES_2_0, "geometry", source_crs,
        False, False, requiresFilterElement=True,
    )
    if element.isNull():
        raise RuntimeError("Could not serialize the analysis polygon filter.")
    document.appendChild(element)
    if len(quote(document.toString(), safe="")) > MAX_ENCODED_POLYGON_FILTER_BYTES:
        return "", "bbox_filter_size"
    return expression, "aoi_intersects"


def _polygonal_geometry(geometry):
    """Return valid polygonal components as a MultiPolygon, or None if absent."""
    if geometry.isNull() or geometry.isEmpty():
        return None
    if QgsWkbTypes.geometryType(geometry.wkbType()) == QgsWkbTypes.PolygonGeometry:
        polygon_parts = [QgsGeometry(geometry)]
    elif QgsWkbTypes.flatType(geometry.wkbType()) == QgsWkbTypes.GeometryCollection:
        # Intersections and makeValid() can return mixed collections; only area
        # geometries can contribute to this polygon-classification workflow.
        polygon_parts = []
        for part in geometry.asGeometryCollection():
            polygonal_part = _polygonal_geometry(part)
            if polygonal_part is not None:
                polygon_parts.append(polygonal_part)
    else:
        return None
    if not polygon_parts:
        return None
    try:
        polygonal = (
            QgsGeometry(polygon_parts[0]) if len(polygon_parts) == 1
            else QgsGeometry.unaryUnion(polygon_parts)
        )
        polygonal.convertToMultiType()
    except Exception as exc:
        raise ValueError("Could not combine polygon components: {0}".format(exc))
    if (polygonal.isNull() or polygonal.isEmpty()
            or QgsWkbTypes.geometryType(polygonal.wkbType()) != QgsWkbTypes.PolygonGeometry
            or not polygonal.isGeosValid()):
        raise ValueError("Polygon components did not produce a valid polygon geometry.")
    return polygonal


def _repair_polygon_geometry(geometry):
    """Repair invalid source geometry and retain only polygonal components."""
    repaired = geometry.makeValid()
    if repaired.isNull() or repaired.isEmpty():
        return None
    return _polygonal_geometry(repaired)


@dataclass(frozen=True)
class _SourceReadContext:
    """Values and run policy needed to read one configured source."""

    layer: object
    service_id: str
    source_name: str
    run_id: str
    metadata: dict
    aoi: object
    transform_context: object
    feedback: object
    language: str
    progress_start: int
    progress_end: int
    selected_feature_ids: object = None
    selected_feature_snapshot: object = None


def _source_feature_iterator(context, filter_rect, selected_feature_id_set,
                             request_started, inverse_transform):
    """Prepare the selected-feature snapshot or provider iterator."""
    layer = context.layer
    service_id = context.service_id
    language = context.language
    feedback = context.feedback
    run_id = context.run_id
    if context.selected_feature_snapshot is not None:
        snapshot_features = []
        for feature_id, geometry_wkb, attributes in context.selected_feature_snapshot:
            source_feature = QgsFeature(layer.fields())
            source_feature.setId(feature_id)
            geometry = QgsGeometry()
            geometry.fromWkb(geometry_wkb)
            if geometry.isNull():
                raise QgsProcessingException(tr(
                    language, "source_feature_geometry_invalid",
                    source=service_id, feature_id=feature_id,
                ))
            source_feature.setGeometry(geometry)
            source_feature.setAttributes(list(attributes))
            snapshot_features.append(source_feature)
        logger.info(
            "run_id=%s stage=source_retrieval source=%s event=selected_local_snapshot_ready feature_count=%d",
            run_id, service_id, len(snapshot_features),
        )
        return iter(snapshot_features), "", "selected_snapshot"

    # The bounded analysis request also initializes a fresh WFS cache. Opening
    # and immediately closing a preliminary zero-limit iterator can leave its
    # downloader racing this read, returning the same provider feature twice.
    request = QgsFeatureRequest()
    spatial_filter = "bbox"
    if selected_feature_id_set is not None:
        request.setFilterFids(sorted(selected_feature_id_set))
        spatial_filter = "selected_fids"
    else:
        request.setFilterRect(filter_rect)
        request.setFlags(Qgis.FeatureRequestFlag.ExactIntersect)
        if layer.providerType().lower() == "wfs":
            source_aoi = QgsGeometry(context.aoi)
            try:
                _apply_coordinate_transform(source_aoi, inverse_transform)
                if not source_aoi.isGeosValid() or source_aoi.isEmpty():
                    raise ValueError("Invalid transformed analysis polygon.")
                expression, spatial_filter = _polygon_request_expression(
                    source_aoi, layer.crs().authid(),
                )
            except Exception as exc:
                raise QgsProcessingException(tr(
                    language, "error_extent_transform", source=service_id, detail=exc,
                )) from exc
            if expression:
                request.setFilterExpression(expression)
    if feedback is not None:
        request.setFeedback(feedback)
    logger.info(
        "run_id=%s stage=source_retrieval source=%s event=wfs_request_started feature_type=%s request_bbox_restricted=%s exact_rect_intersection=%s selected_feature_filter=%s selected_feature_count=%s spatial_filter=%s",
        run_id, service_id, context.metadata["feature_type"],
        selected_feature_id_set is None, selected_feature_id_set is None,
        selected_feature_id_set is not None,
        len(selected_feature_id_set) if selected_feature_id_set is not None else 0,
        spatial_filter,
    )
    try:
        source_iterator = iter(layer.getFeatures(request))
        logger.info(
            "run_id=%s stage=source_retrieval source=%s event=feature_iterator_created elapsed_seconds=%.3f",
            run_id, service_id, time.perf_counter() - request_started,
        )
        return source_iterator, "", spatial_filter
    except Exception as exc:
        logger.exception(
            "run_id=%s stage=source_retrieval source=%s event=feature_iterator_failed",
            run_id, service_id,
        )
        return iter(()), safe_source_error(exc), spatial_filter


def _clip_source_geometry(context, source_feature, transform, filter_rect):
    """Apply the source geometry policy and return clipped polygon evidence."""
    service_id = context.service_id
    language = context.language
    geometry = QgsGeometry(source_feature.geometry())
    if geometry.isNull() or geometry.isEmpty():
        raise QgsProcessingException(tr(
            language, "source_feature_geometry_invalid",
            source=service_id, feature_id=source_feature.id(),
        ))

    repaired = False
    if not geometry.isGeosValid():
        try:
            geometry = _repair_polygon_geometry(geometry)
        except Exception:
            geometry = None
        if geometry is None:
            raise QgsProcessingException(tr(
                language, "source_feature_geometry_invalid",
                source=service_id, feature_id=source_feature.id(),
            ))
        repaired = True

    # Provider rectangle filters can return candidates; the transformed
    # intersection with the actual AOI below determines whether evidence remains.
    source_bbox_matches_request = geometry.boundingBox().intersects(filter_rect)
    try:
        _apply_coordinate_transform(geometry, transform)
        clipped = geometry.intersection(context.aoi)
    except Exception as exc:
        raise QgsProcessingException(tr(
            language, "source_feature_geometry_failed",
            source=service_id, feature_id=source_feature.id(), detail=exc,
        ))
    if clipped.isNull():
        raise QgsProcessingException(tr(
            language, "source_feature_geometry_failed",
            source=service_id, feature_id=source_feature.id(), detail="null intersection result",
        ))
    try:
        polygonal_clipped = _polygonal_geometry(clipped)
    except Exception as exc:
        raise QgsProcessingException(tr(
            language, "source_feature_geometry_failed",
            source=service_id, feature_id=source_feature.id(), detail=exc,
        ))
    if polygonal_clipped is None:
        return None, repaired, "non_polygonal", source_bbox_matches_request

    clipped = polygonal_clipped
    if clipped.isEmpty():
        return None, repaired, "empty", source_bbox_matches_request
    if not clipped.isGeosValid():
        raise QgsProcessingException(tr(
            language, "source_feature_geometry_failed",
            source=service_id, feature_id=source_feature.id(), detail="invalid intersection result",
        ))
    if clipped.area() <= AREA_TOLERANCE_M2:
        return None, repaired, "zero_area", source_bbox_matches_request
    return clipped, repaired, "", source_bbox_matches_request


def _source_feature_identifier(source_feature, source_id_field):
    """Use stable source IDs, falling back to provider feature IDs for null IDs."""
    identifier = source_feature[source_id_field] if source_id_field else None
    is_null_identifier = (
        identifier is None
        or (hasattr(identifier, "isNull") and identifier.isNull())
        or not str(identifier).strip()
    )
    fallback_used = is_null_identifier
    if fallback_used:
        identifier = source_feature.id()
    return str(identifier), fallback_used


def _source_feature_evidence(context, snapshot, source_feature, clipped, source_id_field):
    """Build normalized evidence and the matching clipped source snapshot feature."""
    layer = context.layer
    identifier, fallback_used = _source_feature_identifier(source_feature, source_id_field)
    attributes = dict(zip(
        [field.name() for field in layer.fields()], source_feature.attributes(),
    ))
    evidence = {
        "geometry": clipped,
        "source_id": identifier,
        "service_id": context.service_id,
        "attributes": attributes,
        "values": normalize_source_attributes(attributes, context.metadata["field_map"]),
    }
    if context.service_id == "forest_centre_gridcell":
        # Compare original versions, not only the shape remaining inside the AOI.
        evidence["source_geometry_wkb"] = bytes(source_feature.geometry().asWkb())
    snapshot_feature = QgsFeature(snapshot.fields())
    snapshot_geometry = QgsGeometry(clipped)
    snapshot_geometry.convertToMultiType()
    snapshot_feature.setGeometry(snapshot_geometry)
    snapshot_feature.setAttributes(source_feature.attributes())
    return evidence, snapshot_feature, fallback_used


def _source_coverage(context, source_id_strategy, features,
                     inspected_feature_count, non_overlapping_feature_count,
                     repaired_feature_count, repaired_feature_ids,
                     selected_feature_id_set, source_id_fallback_count,
                     coverage_message, spatial_filter):
    """Assemble stable retrieval provenance and coverage fields."""
    layer = context.layer
    metadata = context.metadata
    return {
        "service_id": context.service_id,
        "status": "AVAILABLE",
        "feature_count": len(features),
        "inspected_feature_count": inspected_feature_count,
        "skipped_feature_count": non_overlapping_feature_count,
        "non_overlapping_feature_count": non_overlapping_feature_count,
        "geometry_repaired_feature_count": repaired_feature_count,
        "geometry_repaired_feature_id_sample": repaired_feature_ids,
        "selected_feature_filter_count": (
            len(context.selected_feature_snapshot)
            if context.selected_feature_snapshot is not None
            else len(selected_feature_id_set) if selected_feature_id_set is not None
            else None
        ),
        "endpoint": metadata["endpoint"],
        "feature_type": metadata["feature_type"],
        "source_crs": layer.crs().authid(),
        "provider": layer.providerType(),
        "spatial_filter": spatial_filter,
        "source_id_strategy": source_id_strategy,
        "source_id_fallback_count": source_id_fallback_count,
        "query_time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "schema": metadata["properties"],
        "skipped_feature_ids": [],
        "skipped_reasons": {
            "bbox_candidate_outside_aoi": non_overlapping_feature_count,
        } if non_overlapping_feature_count else {},
        "request_error": "",
        "message": coverage_message,
    }


def _read_source(context):
    """Acquire one source and apply its geometry and provenance policies."""
    layer = context.layer
    service_id = context.service_id
    source_name = context.source_name
    run_id = context.run_id
    transform_context = context.transform_context
    feedback = context.feedback
    language = context.language
    progress_start = context.progress_start
    progress_end = context.progress_end

    data_provider = layer.dataProvider()
    if layer.thread() != QThread.currentThread() or data_provider.thread() != QThread.currentThread():
        raise QgsProcessingException(tr(language, "source_request_failed",
                                        detail=service_id + ": SOURCE_THREAD_OWNERSHIP_VIOLATION"))
    # Flush earlier queued failures before clearing them, so a successful retry
    # is judged by this request's errors rather than stale provider state.
    QCoreApplication.sendPostedEvents(data_provider, QEvent.Type.MetaCall)
    data_provider.clearErrors()

    if not layer.crs().isValid():
        raise QgsProcessingException(tr(language, "error_source_crs", source=service_id))

    logger.info(
        "run_id=%s stage=source_retrieval source=%s event=request_preparation_started source_crs=%s target_crs=EPSG:3067",
        run_id, service_id, layer.crs().authid(),
    )
    source_id_field = source_identifier_field(layer, service_id)
    source_id_strategy = (
        "attribute:{0};provider_feature_id_fallback_for_null".format(source_id_field)
        if source_id_field else "provider_feature_id"
    )
    try:
        transform = QgsCoordinateTransform(layer.crs(), TARGET_CRS, transform_context)
        inverse_transform = QgsCoordinateTransform(TARGET_CRS, layer.crs(), transform_context)
        filter_rect = inverse_transform.transformBoundingBox(context.aoi.boundingBox())
    except Exception as exc:
        raise QgsProcessingException(tr(language, "error_extent_transform", source=service_id, detail=exc))
    logger.info(
        "run_id=%s stage=source_retrieval source=%s event=request_bounds_ready source_crs=%s",
        run_id, service_id, layer.crs().authid(),
    )

    snapshot = QgsVectorLayer("MultiPolygon?crs=EPSG:3067", service_id, "memory")
    snapshot_provider = snapshot.dataProvider()
    require_provider_success(snapshot_provider.addAttributes(layer.fields()), "{0} snapshot fields".format(service_id))
    snapshot.updateFields()
    logger.info(
        "run_id=%s stage=source_retrieval source=%s event=snapshot_ready field_count=%d",
        run_id, service_id, len(layer.fields()),
    )

    features = []
    kept = []
    inspected_feature_count = 0
    non_overlapping_feature_count = 0
    repaired_feature_count = 0
    repaired_feature_ids = []
    source_id_fallback_count = 0
    last_reported_progress = progress_start
    selected_feature_id_set = (
        set(context.selected_feature_ids)
        if context.selected_feature_ids is not None else None
    )
    matched_selected_feature_ids = set()
    request_started = time.perf_counter()
    source_iterator, request_error, spatial_filter = _source_feature_iterator(
        context, filter_rect, selected_feature_id_set, request_started, inverse_transform,
    )

    while True:
        _check_cancelled(feedback, language)
        if feedback is not None and hasattr(feedback, "setProgressText"):
            feedback.setProgressText(tr(
                language, "progress_source_checking", source=source_name,
                count=inspected_feature_count,
            ))
        if inspected_feature_count <= 20 or inspected_feature_count % 100 == 0:
            logger.info(
                "run_id=%s stage=source_retrieval source=%s event=checking_for_more_source_features received_feature_count=%d",
                run_id, service_id, inspected_feature_count,
            )
        next_started = time.perf_counter()
        try:
            source_feature = next(source_iterator)
        except StopIteration:
            logger.info(
                "run_id=%s stage=source_retrieval source=%s event=source_iterator_exhausted received_feature_count=%d elapsed_seconds=%.3f",
                run_id, service_id, inspected_feature_count,
                time.perf_counter() - request_started,
            )
            break
        except Exception as exc:
            request_error = safe_source_error(exc)
            logger.exception(
                "run_id=%s stage=source_retrieval source=%s event=feature_iteration_failed inspected_feature_count=%d",
                run_id, service_id, inspected_feature_count,
            )
            break
        _check_cancelled(feedback, language)
        inspected_feature_count += 1
        if inspected_feature_count <= 20 or inspected_feature_count % 100 == 0:
            logger.info(
                "run_id=%s stage=source_retrieval source=%s event=source_feature_received received_feature_count=%d wait_seconds=%.3f elapsed_seconds=%.3f",
                run_id, service_id, inspected_feature_count,
                time.perf_counter() - next_started,
                time.perf_counter() - request_started,
            )
        if feedback is not None and hasattr(feedback, "setProgress"):
            # WFS has no AOI-filtered total to estimate against. Cap activity progress
            # below completion so the later source-complete update can finish the interval.
            fraction = min(inspected_feature_count / 100.0, 0.95)
            progress = progress_start + (progress_end - progress_start) * fraction
            if int(progress) > last_reported_progress:
                feedback.setProgress(progress)
                last_reported_progress = int(progress)
        if inspected_feature_count % 500 == 0 and feedback is not None:
            logger.info(
                "run_id=%s stage=source_retrieval source=%s event=features_inspected count=%d",
                run_id, service_id, inspected_feature_count,
            )
            message = tr(
                language, "progress_source_items", source=source_name,
                count=inspected_feature_count,
            )
            if hasattr(feedback, "setProgressText"):
                feedback.setProgressText(message)
            if hasattr(feedback, "pushInfo"):
                feedback.pushInfo(message)

        if (selected_feature_id_set is not None and context.selected_feature_snapshot is None
                and source_feature.id() not in selected_feature_id_set):
            continue
        if selected_feature_id_set is not None and context.selected_feature_snapshot is None:
            matched_selected_feature_ids.add(source_feature.id())

        clipped, repaired, skip_reason, source_bbox_matches_request = _clip_source_geometry(
            context, source_feature, transform, filter_rect,
        )
        if repaired:
            repaired_feature_count += 1
            if len(repaired_feature_ids) < 20:
                repaired_feature_ids.append(_source_feature_identifier(source_feature, source_id_field)[0])
        if skip_reason:
            non_overlapping_feature_count += 1
            if skip_reason in ("empty", "zero_area") and non_overlapping_feature_count <= 20:
                log_fields = (
                    "run_id=%s stage=source_retrieval source=%s event=feature_outside_aoi "
                    "provider_feature_id=%s candidate_bbox_intersects_request_bounds=%s"
                )
                if skip_reason == "zero_area":
                    log_fields += " intersection_area=0"
                logger.info(
                    log_fields, run_id, service_id, source_feature.id(),
                    source_bbox_matches_request,
                )
            continue

        evidence, snapshot_feature, fallback_used = _source_feature_evidence(
            context, snapshot, source_feature, clipped, source_id_field,
        )
        features.append(evidence)
        kept.append(snapshot_feature)
        if fallback_used and source_id_field:
            source_id_fallback_count += 1

    # WFS downloads run in another thread. Its failure is queued to this
    # provider, so iterator exhaustion alone cannot establish successful empty
    # coverage. Deliver only this owned provider's queued calls before reading
    # its errors; do not process unrelated application/UI events.
    if hasattr(source_iterator, "close"):
        source_iterator.close()
    QCoreApplication.sendPostedEvents(data_provider, QEvent.Type.MetaCall)
    _check_cancelled(feedback, language)
    provider_errors = data_provider.errors()
    if provider_errors and not request_error:
        request_error = safe_source_error("\n".join(provider_errors))
    if request_error:
        raise QgsProcessingException(tr(
            language, "source_request_failed", detail="{0}: {1}".format(service_id, request_error)
        ))
    if selected_feature_id_set is not None:
        missing_selected_ids = selected_feature_id_set - matched_selected_feature_ids
        if missing_selected_ids:
            missing_sample = ", ".join(
                str(feature_id) for feature_id in sorted(missing_selected_ids)[:20]
            )
            raise QgsProcessingException(tr(
                language, "source_selected_features_missing",
                source=service_id, count=len(missing_selected_ids), features=missing_sample,
            ))
    if non_overlapping_feature_count:
        logger.info(
            "run_id=%s stage=source_retrieval source=%s event=bbox_candidates_outside_aoi count=%d",
            run_id, service_id, non_overlapping_feature_count,
        )
    if repaired_feature_count:
        repaired_id_sample = ", ".join(repaired_feature_ids)
        logger.warning(
            "run_id=%s stage=source_retrieval source=%s event=invalid_geometries_repaired count=%d feature_id_sample=%s",
            run_id, service_id, repaired_feature_count, repaired_id_sample,
        )
        if feedback is not None:
            warning = tr(
                language, "source_geometry_repaired",
                source=service_id, count=repaired_feature_count,
                features=repaired_id_sample,
            )
            if hasattr(feedback, "pushWarning"):
                feedback.pushWarning(warning)
            elif hasattr(feedback, "pushInfo"):
                feedback.pushInfo(warning)

    duplicate_count = 0
    if service_id == "forest_centre_gridcell":
        unique, positions = deduplicate_grid_records(features, language, feedback)
        duplicate_count = len(features) - len(unique)
        features = unique
        kept = [kept[position] for position in positions]
    require_provider_success(
        snapshot_provider.addFeatures(kept),
        "{0} snapshot features ({1} attempted)".format(service_id, len(kept)),
        snapshot_provider,
    )
    snapshot.updateExtents()
    if not features:
        if non_overlapping_feature_count:
            coverage_message = tr(
                language, "source_no_aoi_overlap", count=non_overlapping_feature_count,
            )
        else:
            coverage_message = tr(language, "source_no_features")
    else:
        coverage_message = tr(language, "source_observed_features")
    coverage = _source_coverage(
        context, source_id_strategy, features,
        inspected_feature_count, non_overlapping_feature_count,
        repaired_feature_count, repaired_feature_ids,
        selected_feature_id_set, source_id_fallback_count, coverage_message, spatial_filter,
    )
    if service_id == "forest_centre_gridcell":
        coverage["deduplicated_feature_count"] = duplicate_count
        coverage["provider_fields"] = list(context.metadata["provider_fields"])
        coverage["field_map"] = dict(context.metadata["field_map"])
    return features, coverage, snapshot


def retrieve_sources(inputs, feedback=None):
    """Read each configured source once and retain its clipped snapshot."""
    language = inputs["language"]
    coverage = []
    source_features = {}
    snapshots = []
    protected_available = True
    source_count = len(inputs["service_ids"])
    logger.info(
        "run_id=%s stage=source_retrieval started source_count=%d",
        inputs["run_id"], source_count,
    )
    for index, service_id in enumerate(inputs["service_ids"]):
        _check_cancelled(feedback, language)
        progress_start = 10 + 60 * index / max(source_count, 1)
        progress_end = 10 + 60 * (index + 1) / max(source_count, 1)
        source_name = inputs["source_display_names"][service_id]
        source_message = tr(language, "progress_source", source=source_name)
        if feedback is not None and hasattr(feedback, "setProgress"):
            feedback.setProgress(progress_start)
        if feedback is not None and hasattr(feedback, "pushInfo"):
            feedback.pushInfo(source_message)
            if hasattr(feedback, "setProgressText"):
                feedback.setProgressText(source_message)
        source_started = time.perf_counter()
        layer = inputs["layers"][service_id]
        logger.info(
            "run_id=%s stage=source_retrieval source=%s event=started source_index=%d source_total=%d",
            inputs["run_id"], service_id, index + 1, source_count,
        )
        if feedback is not None:
            if hasattr(feedback, "setProgressText"):
                feedback.setProgressText(source_message)
            if hasattr(feedback, "pushInfo"):
                feedback.pushInfo(tr(language, "progress_source_activity", source=source_name))
        try:
            context = _SourceReadContext(
                layer=layer,
                service_id=service_id,
                source_name=source_name,
                run_id=inputs["run_id"],
                metadata=inputs["source_metadata"][service_id],
                aoi=inputs["aoi"],
                transform_context=inputs["transform_context"],
                feedback=feedback,
                language=language,
                progress_start=progress_start,
                progress_end=progress_end,
                selected_feature_ids=inputs.get("selected_source_feature_ids", {}).get(service_id),
                selected_feature_snapshot=inputs.get("selected_source_feature_snapshots", {}).get(service_id),
            )
            features, status, snapshot = _read_source(context)
        except Exception:
            logger.exception(
                "run_id=%s stage=source_retrieval source=%s event=failed",
                inputs["run_id"], service_id,
            )
            raise
        logger.info(
            "run_id=%s stage=source_retrieval source=%s event=completed source_index=%d source_total=%d status=%s feature_count=%d inspected_feature_count=%d non_overlapping_feature_count=%d elapsed_seconds=%.3f",
            inputs["run_id"], service_id, index + 1, source_count, status["status"], status["feature_count"],
            status["inspected_feature_count"], status["non_overlapping_feature_count"],
            time.perf_counter() - source_started,
        )
        status["schema_discovered_at"] = inputs["source_metadata"][service_id]["query_time"]
        source_features[service_id] = features
        coverage.append(status)
        if feedback is not None and hasattr(feedback, "pushInfo"):
            feedback.pushInfo(tr(
                language, "progress_source_complete",
                source=inputs["source_display_names"][service_id], count=status["feature_count"],
            ))
        if service_id in PROTECTED_SOURCE_IDS:
            protected_available = protected_available and status["status"] == "AVAILABLE"
        if snapshot is not None:
            snapshots.append((service_id, snapshot))
        if feedback is not None and hasattr(feedback, "setProgress"):
            feedback.setProgress(progress_end)
    logger.info(
        "run_id=%s stage=source_retrieval completed source_count=%d total_clipped_feature_count=%d",
        inputs["run_id"], source_count,
        sum(len(source_features.get(service_id, ())) for service_id in inputs["service_ids"]),
    )
    grid_sampler = GridCellSampler(source_features.get("forest_centre_gridcell", ()), language, feedback)
    return {
        "coverage": coverage,
        "source_features": source_features,
        "protected_areas_status": "AVAILABLE" if protected_available else "NOT_AVAILABLE",
        "snapshots": snapshots,
        "grid_sampler": grid_sampler,
    }

