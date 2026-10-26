"""Localized, idempotent QGIS project setup."""

import json

from qgis.core import (
    QgsFillSymbol, QgsLayerTreeNode, QgsProject, QgsRasterLayer,
    QgsSingleSymbolRenderer, QgsVectorLayer,
)

from ..i18n import source_readiness_message, tr
from .source_layers import provider_field_names
from .sources import (
    SERVICE_DEFINITIONS, SourceError, inspect_service, qgis_wfs_uri,
    safe_source_error, syke_user_id,
)
from ..analysis.source_readiness import assess_source_schema


GROUP_IDS = (
    ("results", "results_group"),
    ("references", "references_group"),
    ("basemaps", "basemaps_group"),
)
RESULTS_LAYER_ID = "classified_forest_polygons"
OSM_LAYER_ID = "osm_xyz"
DETAILED_REFERENCE_SERVICE_IDS = frozenset(("forest_centre_stand", "forest_centre_habitat"))
REFERENCE_MINIMUM_VISIBLE_SCALE = 500000.0
GRID_MINIMUM_VISIBLE_SCALE = 300.0


def _managed_node(parent, property_name, property_value):
    for child in parent.children():
        if child.customProperty(property_name, "") == property_value:
            return child
        if child.nodeType() == QgsLayerTreeNode.NodeGroup:
            found = _managed_node(child, property_name, property_value)
            if found is not None:
                return found
    return None


def _managed_layer(project, property_name, property_value):
    return next((
        layer for layer in project.mapLayers().values()
        if layer.customProperty(property_name, "") == property_value
    ), None)


def _disable_legacy_protected_layer(project, language):
    """Hide the former single protected layer so it cannot be reused by mistake."""
    layer = _managed_layer(project, "savonia/service_id", "syke_protected_areas")
    if layer is None:
        return
    layer.setCustomProperty("savonia/legacy_service_id", "syke_protected_areas")
    layer.setCustomProperty("savonia/service_id", "")
    layer.setName(tr(language, "legacy_protected_layer"))
    node = project.layerTreeRoot().findLayer(layer.id())
    if node is not None:
        node.setItemVisibilityChecked(False)


def _place_layer_in_group(project, group, layer):
    node = project.layerTreeRoot().findLayer(layer.id())
    if node is not None and node.parent() == group:
        return node
    if node is None:
        return group.addLayer(layer)
    bridge = project.layerTreeRegistryBridge()
    bridge_was_enabled = bridge.isEnabled()
    bridge.setEnabled(False)
    try:
        node.parent().takeChild(node)
        group.addChildNode(node)
    finally:
        bridge.setEnabled(bridge_was_enabled)
    return node


def _setup_readiness(service_id, field_names, language):
    readiness = assess_source_schema(service_id, field_names)
    message = source_readiness_message(language, readiness)
    if readiness["status"] == "AVAILABLE" and service_id == "forest_centre_stand":
        return "AVAILABLE", tr(language, "source_setup_stand_unmapped"), readiness
    return readiness["status"], message, readiness


def _syke_id_notice(service_id, language):
    if service_id.startswith("syke_") and not syke_user_id():
        return tr(language, "syke_id_recommended")
    return ""


def _style_forest_source(layer, service_id):
    """Apply stable project colors to the stand and habitat polygon layers."""
    styles = {
        "forest_centre_stand": {
            "color": "75,150,85,255",
            "outline_color": "40,105,50,255",
            "outline_width": "0.25",
        },
        "forest_centre_habitat": {
            "color": "175,220,150,220",
            "outline_color": "105,155,80,255",
            "outline_width": "0.35",
        },
        "syke_groundwater_areas": {
            "color": "95,175,220,95",
            "outline_color": "55,115,165,220",
            "outline_width": "0.35",
        },
    }
    style = styles.get(service_id)
    if style is not None:
        layer.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple(style)))
    if service_id in DETAILED_REFERENCE_SERVICE_IDS:
        # QGIS minimumScale is the most zoomed-out visible scale. At smaller
        # denominators (closer zooms) these detailed WFS layers remain visible.
        layer.setMinimumScale(REFERENCE_MINIMUM_VISIBLE_SCALE)
        layer.setMaximumScale(0.0)
        layer.setScaleBasedVisibility(True)
    elif service_id == "forest_centre_gridcell":
        # QGIS 4.2 excludes an equal minimum scale with a comparison tolerance.
        # A one-millionth-denominator margin includes 1:300 at that tolerance.
        layer.setMinimumScale(GRID_MINIMUM_VISIBLE_SCALE + 1e-6)
        layer.setMaximumScale(0.0)
        layer.setScaleBasedVisibility(True)


def _place_grid_last(project, group):
    """Move only the managed grid; preserve all other reference-layer order."""
    layer = _managed_layer(project, "savonia/service_id", "forest_centre_gridcell")
    if layer is None:
        return
    node = _place_layer_in_group(project, group, layer)
    if group.children()[-1] == node:
        return
    bridge = project.layerTreeRegistryBridge()
    bridge_was_enabled = bridge.isEnabled()
    bridge.setEnabled(False)
    try:
        group.takeChild(node)
        group.addChildNode(node)
    finally:
        bridge.setEnabled(bridge_was_enabled)


def _localized_group(root, group_id, label):
    node = _managed_node(root, "savonia/group_id", group_id)
    if node is None:
        node = root.addGroup(label)
        node.setCustomProperty("savonia/group_id", group_id)
    else:
        node.setName(label)
    return node


def _move_group_to_index(project, root, group, index):
    if root.children()[index] == group:
        return group
    bridge = project.layerTreeRegistryBridge()
    bridge_was_enabled = bridge.isEnabled()
    bridge.setEnabled(False)
    try:
        # QGIS 4.2 takeChild(group) detaches its children as well. Clone the
        # tree nodes before removal so user reference layers/order survive.
        replacement = group.clone()
        root.removeChildNode(group)
        root.insertChildNode(index, replacement)
    finally:
        bridge.setEnabled(bridge_was_enabled)
    return replacement


def ensure_group_order(project, language):
    root = project.layerTreeRoot()
    groups = []
    for group_id, label_key in GROUP_IDS:
        groups.append(_localized_group(root, group_id, tr(language, label_key)))
    for index, group_id in enumerate(("results", "references", "basemaps")):
        current = _managed_node(root, "savonia/group_id", group_id)
        _move_group_to_index(project, root, current, index)
    # A custom order can override tree order. Reset it to the layer-tree order
    # so the visible tree and map rendering follow the same documented stack.
    try:
        root.setHasCustomLayerOrder(False)
        root.setCustomLayerOrder(root.layerOrder())
    except AttributeError:
        pass
    return {
        group_id: _managed_node(root, "savonia/group_id", group_id)
        for group_id, _label_key in GROUP_IDS
    }


def results_group(project, language):
    """Return the existing results group, creating only that group if needed."""
    root = project.layerTreeRoot()
    group = _managed_node(root, "savonia/group_id", "results")
    if group is None:
        group = root.addGroup(tr(language, "results_group"))
        group.setCustomProperty("savonia/group_id", "results")
    return group


def _add_or_relabel_wfs(project, group, service_id, language):
    definition = SERVICE_DEFINITIONS[service_id]
    label = tr(language, definition["name_key"])
    layer = _managed_layer(project, "savonia/service_id", service_id)
    if layer is not None:
        _place_layer_in_group(project, group, layer)
        layer.setName(label)
        if not layer.isValid():
            return layer, {"service_id": service_id, "status": "INVALID_LAYER", "message": tr(language, "source_configured_invalid")}
        _style_forest_source(layer, service_id)
        try:
            metadata = inspect_service(service_id)
        except SourceError as exc:
            return layer, {
                "service_id": service_id, "status": "UNAVAILABLE", "error_code": exc.code,
                "message": tr(language, "source_discovery_detail", detail="{0}: {1}".format(exc.code, safe_source_error(exc.message))),
            }
        configured_type = layer.customProperty("savonia/feature_type", "")
        if configured_type and configured_type != metadata["feature_type"]:
            layer.setCustomProperty("savonia/schema_changed_to", metadata["feature_type"])
            return layer, {
                "service_id": service_id,
                "status": "SCHEMA_CHANGED",
                "message": tr(language, "source_schema_changed", old=configured_type, new=metadata["feature_type"]),
                "metadata": metadata,
            }
        layer.setCustomProperty("savonia/schema_changed_to", "")
        layer.setCustomProperty("savonia/query_time", metadata["query_time"])
        layer.setCustomProperty("savonia/schema_json", json.dumps(metadata["properties"], ensure_ascii=False))
        status, message, readiness = _setup_readiness(
            service_id, provider_field_names(layer), language
        )
        message = "; ".join(
            value for value in (message, _syke_id_notice(service_id, language)) if value
        )
        return layer, {
            "service_id": service_id, "status": status, "message": message,
            "readiness": readiness, "metadata": metadata, "layer": layer,
        }
    try:
        metadata = inspect_service(service_id)
    except SourceError as exc:
        return None, {
            "service_id": service_id,
            "status": "UNAVAILABLE",
            "error_code": exc.code,
            "message": tr(language, "source_discovery_detail", detail="{0}: {1}".format(exc.code, safe_source_error(exc.message))),
        }
    layer = QgsVectorLayer(qgis_wfs_uri(metadata), label, "WFS")
    if not layer.isValid():
        return None, {
            "service_id": service_id,
            "status": "INVALID_LAYER",
            "error_code": "INVALID_WFS_LAYER",
            "message": tr(language, "source_layer_create_failed", feature_type=metadata["feature_type"]),
            "metadata": metadata,
        }
    _style_forest_source(layer, service_id)
    layer.setCustomProperty("savonia/service_id", service_id)
    layer.setCustomProperty("savonia/endpoint", metadata["endpoint"])
    layer.setCustomProperty("savonia/feature_type", metadata["feature_type"])
    layer.setCustomProperty("savonia/source_crs", metadata["source_crs"])
    layer.setCustomProperty("savonia/query_time", metadata["query_time"])
    layer.setCustomProperty("savonia/schema_json", json.dumps(metadata["properties"], ensure_ascii=False))
    project.addMapLayer(layer, False)
    _place_layer_in_group(project, group, layer)
    status, message, readiness = _setup_readiness(
        service_id, provider_field_names(layer), language
    )
    message = "; ".join(
        value for value in (message, _syke_id_notice(service_id, language)) if value
    )
    return layer, {
        "service_id": service_id, "status": status, "message": message,
        "readiness": readiness, "metadata": metadata, "layer": layer,
    }


def _remove_empty_results_placeholder(project):
    """Remove the obsolete setup layer without touching completed run outputs."""
    for layer in list(project.mapLayers().values()):
        if (
            layer.customProperty("savonia/layer_id", "") == RESULTS_LAYER_ID
            and layer.providerType() == "memory"
            and layer.featureCount() == 0
        ):
            project.removeMapLayer(layer.id())


def _ensure_osm(project, basemaps_group, language):
    layer = _managed_layer(project, "savonia/layer_id", OSM_LAYER_ID)
    if layer is not None:
        layer.setName(tr(language, "osm_layer"))
        _place_layer_in_group(project, basemaps_group, layer)
        return layer
    layer = QgsRasterLayer(
        "type=xyz&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png&zmin=0&zmax=19",
        tr(language, "osm_layer"),
        "wms",
    )
    if not layer.isValid():
        return None
    layer.setCustomProperty("savonia/layer_id", OSM_LAYER_ID)
    layer.setCustomProperty("savonia/managed", True)
    project.addMapLayer(layer, False)
    basemaps_group.addLayer(layer)
    return layer


def setup_project(project=None, language="en"):
    """Create/reuse groups and configured online source layers.

    This operation does not process sources outside V1 scope.
    Failed source discovery is returned as coverage information for the UI.
    """
    project = project or QgsProject.instance()
    groups = ensure_group_order(project, language)
    _disable_legacy_protected_layer(project, language)
    statuses = []
    # Layer-tree order is top to bottom, and addLayer() appends. Create habitat
    # before stands so habitat polygons render above the stand polygons.
    setup_order = ("forest_centre_habitat", "forest_centre_stand") + tuple(
        service_id for service_id in SERVICE_DEFINITIONS
        if service_id not in ("forest_centre_habitat", "forest_centre_stand")
    )
    for service_id in setup_order:
        layer, status = _add_or_relabel_wfs(project, groups["references"], service_id, language)
        statuses.append(status)
    _place_grid_last(project, groups["references"])
    _remove_empty_results_placeholder(project)
    osm = _ensure_osm(project, groups["basemaps"], language)
    if osm is None:
        statuses.append({"service_id": OSM_LAYER_ID, "status": "INVALID_LAYER", "error_code": "XYZ_LAYER_INVALID"})
    source_statuses = {row["service_id"]: row["status"] for row in statuses}
    required_sources_ready = all(
        source_statuses.get(service_id) == "AVAILABLE"
        for service_id, definition in SERVICE_DEFINITIONS.items()
        if definition["required"]
    )
    return {
        "language": language,
        "ready": required_sources_ready,
        "groups": tuple(group_id for group_id, _key in GROUP_IDS),
        "sources": statuses,
        "out_of_scope": (
            "syke_forest_sensitive_water", "peatlands", "water_protection_buffers",
            "recreation_areas", "potential_protected_sites", "my_areas",
        ),
    }
