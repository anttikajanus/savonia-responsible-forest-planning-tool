"""Readiness rules for configured QGIS source layers."""

import json
import urllib.parse

from ..analysis.source_readiness import assess_source_schema
from ..i18n import source_readiness_message, tr
from .sources import SERVICE_DEFINITIONS


def provider_field_names(layer):
    """Return source-provider fields, excluding project joins and virtual fields."""
    provider = layer.dataProvider()
    return [field.name() for field in provider.fields()] if provider is not None else []


def verify_source_layer(layer, service_id, language="en"):
    """Return provider field resolution and provenance, or a localized error."""
    if layer is None or not layer.isValid() or layer.providerType().lower() != "wfs":
        return None, {
            "reason_code": "SOURCE_LAYER_INVALID",
            "message": tr(language, "source_missing_invalid"),
        }

    definition = SERVICE_DEFINITIONS[service_id]
    expected_endpoint = definition["endpoint"].lower()
    uri = urllib.parse.unquote(layer.source()).lower()
    configured_endpoint = layer.customProperty("savonia/endpoint", "").lower()
    # Layer names are user-editable, so verify the provider identity before
    # trusting the discovery metadata saved on the layer.
    if expected_endpoint not in uri and configured_endpoint != expected_endpoint:
        return None, {
            "reason_code": "SOURCE_ENDPOINT_MISMATCH",
            "message": tr(language, "source_endpoint_mismatch"),
        }

    configured_type = layer.customProperty("savonia/feature_type", "")
    changed_type = layer.customProperty("savonia/schema_changed_to", "")
    if changed_type:
        return None, {
            "reason_code": "SOURCE_FEATURE_TYPE_CHANGED",
            "message": tr(language, "source_schema_changed", old=configured_type, new=changed_type),
        }
    if not configured_type or configured_type.lower() not in uri:
        return None, {
            "reason_code": "SOURCE_FEATURE_TYPE_MISMATCH",
            "message": tr(language, "source_endpoint_mismatch"),
        }

    raw_schema = layer.customProperty("savonia/schema_json", "")
    try:
        properties = json.loads(raw_schema)
    except (TypeError, ValueError):
        properties = None
    metadata = {
        "service_id": service_id,
        "provider": "WFS",
        "endpoint": configured_endpoint or definition["endpoint"],
        "feature_type": configured_type,
        "query_time": layer.customProperty("savonia/query_time", ""),
        "source_crs": layer.customProperty("savonia/source_crs", ""),
        "properties": properties,
    }
    field_names = provider_field_names(layer)
    readiness = assess_source_schema(service_id, field_names)
    if readiness["status"] != "AVAILABLE":
        return None, {
            "reason_code": readiness["reason_code"],
            "message": source_readiness_message(language, readiness),
        }
    if layer.geometryType() != 2:
        return None, {
            "reason_code": "SOURCE_GEOMETRY_TYPE_INVALID",
            "message": tr(language, "source_polygon_required"),
        }
    metadata["provider_fields"] = field_names
    metadata["field_map"] = readiness["field_map"]
    return metadata, None


def source_identifier_field(layer, service_id):
    """Select the stable source attribute used to trace features to their input."""
    actual_fields = {name.lower(): name for name in provider_field_names(layer)}
    candidates = {
        "forest_centre_stand": ("standid",),
        "forest_centre_gridcell": ("gridcellid",),
        "forest_centre_habitat": ("habitatid",),
        "syke_protected_areas_state_owned": ("kohdeid", "lsaluetunnus"),
        "syke_protected_areas_private_land": ("kohdeid", "lsaluetunnus"),
        "syke_protected_areas_wilderness": ("kohdeid", "lsaluetunnus"),
        "syke_nature_conservation_programme_areas": ("lsoaluetunnus", "objectid"),
        "syke_groundwater_areas": ("pohjavesialue_id", "tunnus", "muodaluetunnus"),
    }.get(service_id, ())
    for candidate in candidates:
        field_name = actual_fields.get(candidate)
        if field_name:
            return field_name
    return actual_fields.get("fid")
