"""Validate the AOI, output destination, and configured source layers."""

import os
import re

from qgis.core import QgsCoordinateTransform, QgsGeometry, QgsProcessingException

from ...i18n import tr
from ...adapters.source_layers import verify_source_layer
from ...adapters.sources import SERVICE_DEFINITIONS
from .common import TARGET_CRS, _apply_coordinate_transform


DEFAULT_OUTPUT_NAME_PREFIX = "savonia_responsible_forest_inputs_"


def _validate_output_destination(parameters, run_id, language):
    raw_folder = str(parameters.get("output_folder") or "").strip()
    if not raw_folder:
        raise QgsProcessingException(tr(language, "error_output_folder"))
    folder = os.path.abspath(raw_folder)
    if os.path.exists(folder) and not os.path.isdir(folder):
        raise QgsProcessingException(tr(language, "error_output_writable", path=folder))
    output_name = str(parameters.get("output_name") or DEFAULT_OUTPUT_NAME_PREFIX + run_id).strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,119}", output_name) or output_name in (".", ".."):
        raise QgsProcessingException(tr(language, "error_output_name"))
    check_folder = folder if os.path.isdir(folder) else os.path.dirname(folder)
    if not check_folder or not os.path.isdir(check_folder) or not os.access(check_folder, os.W_OK):
        raise QgsProcessingException(tr(language, "error_output_writable", path=folder))
    if os.path.exists(folder) and not os.access(folder, os.W_OK):
        raise QgsProcessingException(tr(language, "error_output_writable", path=folder))
    gpkg_path = os.path.join(folder, output_name + ".gpkg")
    xlsx_path = os.path.join(folder, output_name + ".xlsx")
    # Never overwrite a previous run; partial-output cleanup later is safe only
    # because these paths were confirmed unused before the run began.
    if os.path.exists(gpkg_path) or os.path.exists(xlsx_path):
        raise QgsProcessingException(tr(language, "error_output_exists"))
    return folder, output_name, gpkg_path, xlsx_path

def _aoi_geometry(layer, selected_only, transform_context, language):
    if layer is None or not layer.isValid():
        raise QgsProcessingException(tr(language, "error_aoi_layer"))
    if layer.geometryType() != 2:
        raise QgsProcessingException(tr(language, "error_aoi_polygon"))
    if not layer.crs().isValid():
        raise QgsProcessingException(tr(language, "error_aoi_crs"))
    features = list(layer.getSelectedFeatures() if selected_only else layer.getFeatures())
    if not features:
        raise QgsProcessingException(tr(language, "error_aoi_empty"))
    transform = QgsCoordinateTransform(layer.crs(), TARGET_CRS, transform_context)
    geometries = []
    for feature in features:
        geometry = QgsGeometry(feature.geometry())
        if geometry.isEmpty() or not geometry.isGeosValid():
            raise QgsProcessingException(
                tr(language, "error_aoi_invalid", feature_id=feature.id())
            )
        try:
            _apply_coordinate_transform(geometry, transform)
        except Exception as exc:
            raise QgsProcessingException(tr(language, "error_aoi_transform", detail=exc))
        geometries.append(geometry)
    if not geometries:
        raise QgsProcessingException(tr(language, "error_aoi_no_valid"))
    # Dissolve overlaps so selected AOI polygons do not duplicate stand area.
    merged = QgsGeometry.unaryUnion(geometries)
    if merged.isNull() or merged.isEmpty() or not merged.isGeosValid() or merged.area() <= 0:
        raise QgsProcessingException(tr(language, "error_aoi_area"))
    return merged

def _source_layer(parameters, service_id):
    explicit_sources = parameters.get("sources")
    return (explicit_sources or {}).get(service_id)

def validate_inputs(parameters, run_id):
    """Validate run inputs and return the explicit values later steps need."""
    language = parameters.get("language", "en")
    transform_context = parameters.get("transform_context")
    if transform_context is None:
        raise QgsProcessingException(tr(language, "error_transform_context"))
    aoi_layer = parameters.get("aoi_layer")
    aoi = _aoi_geometry(aoi_layer, bool(parameters.get("selected_only")), transform_context, language)
    output_folder, base_name, gpkg_path, xlsx_path = _validate_output_destination(
        parameters, run_id, language
    )
    service_ids = tuple(SERVICE_DEFINITIONS)
    layers = {service_id: _source_layer(parameters, service_id) for service_id in service_ids}
    selected_source_feature_ids = {}
    if parameters.get("selected_only"):
        selected_ids = tuple(aoi_layer.selectedFeatureIds())
        for service_id, layer in layers.items():
            if layer is not None and (layer is aoi_layer or layer.id() == aoi_layer.id()):
                selected_source_feature_ids[service_id] = selected_ids
    selected_source_feature_ids.update(
        parameters.get("selected_source_feature_ids") or {}
    )
    source_metadata = {}
    verification_errors = {}
    for service_id in service_ids:
        metadata, error = verify_source_layer(layers[service_id], service_id, language)
        if not error and not layers[service_id].crs().isValid():
            error = {"reason_code": "SOURCE_CRS_INVALID",
                     "message": tr(language, "error_source_crs", source=service_id)}
        if error:
            verification_errors[service_id] = error
            layers[service_id] = None
        else:
            source_metadata[service_id] = metadata
    source_display_names = {
        service_id: tr(language, definition["name_key"])
        for service_id, definition in SERVICE_DEFINITIONS.items()
    }
    for service_id, error in verification_errors.items():
        error["source_name"] = source_display_names[service_id]
    if verification_errors:
        details = "\n".join(
            "{0}: {1}".format(error["source_name"], error["message"])
            for error in verification_errors.values()
        )
        raise QgsProcessingException(tr(language, "error_sources_invalid", details=details))
    return {
        "run_id": run_id,
        "transform_context": transform_context,
        "aoi_crs": aoi_layer.crs().authid(),
        "aoi_name": aoi_layer.name(),
        "language": language,
        "aoi_layer": aoi_layer,
        "aoi": aoi,
        "output_folder": output_folder,
        "base_name": base_name,
        "gpkg_path": gpkg_path,
        "xlsx_path": xlsx_path,
        "service_ids": service_ids,
        "layers": layers,
        "source_metadata": source_metadata,
        "source_display_names": source_display_names,
        "selected_only": bool(parameters.get("selected_only")),
        "selected_source_feature_ids": selected_source_feature_ids,
    }

