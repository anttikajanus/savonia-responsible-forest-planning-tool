"""Localized, idempotent QGIS project setup."""

import json

from qgis.core import (
    Qgis, QgsFillSymbol, QgsLayerTreeNode, QgsLineSymbol, QgsNullSymbolRenderer, QgsPalLayerSettings, QgsProject, QgsRasterLayer,
    QgsSingleSymbolRenderer, QgsTextBufferSettings, QgsTextFormat, QgsVectorLayer, QgsVectorLayerSimpleLabeling,
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor, QFont

from .. import RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX
from ..i18n import source_readiness_message, tr
from .source_layers import provider_field_names, source_layer_geometry_error
from .sources import (
    SERVICE_DEFINITIONS, SourceError, inspect_service, qgis_wfs_uri,
    safe_source_error, syke_user_id, mml_api_key, qgis_mml_uri,
    MML_PARCEL_SERVICE_ID, MML_PARCEL_COLLECTION, MML_PARCEL_LABEL_FIELD,
    MML_IDENTIFIER_SERVICE_ID, MML_IDENTIFIER_COLLECTION,
    qgis_mml_wmts_uri,
)
from ..analysis.source_readiness import assess_source_schema


GROUP_IDS = (
    ("results", "results_group"),
    ("references", "references_group"),
    ("basemaps", "basemaps_group"),
)
RESULTS_LAYER_ID = "classified_forest_polygons"
OSM_LAYER_ID = "osm_xyz"
BASEMAPS = (
    ("mml_ortokuva", "orthophoto_layer", "ortokuva", "image/jpeg"),
    ("mml_maastokartta", "topographic_layer", "maastokartta", "image/png"),
)
DETAILED_REFERENCE_SERVICE_IDS = frozenset(("forest_centre_stand", "forest_centre_habitat"))
FOREST_MINIMUM_VISIBLE_SCALE = 7763.0
REFERENCE_MINIMUM_VISIBLE_SCALE = 25000.0
IDENTIFIER_MINIMUM_VISIBLE_SCALE = 10000.0
GRID_MINIMUM_VISIBLE_SCALE = 300.0
REFERENCE_GROUPS = (
    ("properties", "property_group", (MML_PARCEL_SERVICE_ID, MML_IDENTIFIER_SERVICE_ID)),
    ("forest", "forest_group", ("forest_centre_habitat", "forest_centre_stand", "forest_centre_gridcell")),
    ("protected", "protected_group", (
        "syke_nature_conservation_programme_areas", "syke_protected_areas_wilderness",
        "syke_protected_areas_state_owned", "syke_protected_areas_private_land",
    )),
    ("water", "water_group", (
        "syke_groundwater_areas", "syke_rantaviiva_line_river",
        "syke_rantaviiva_polygon_river", "syke_rantaviiva_lake",
    )),
)
PROTECTED_SERVICE_IDS = frozenset(REFERENCE_GROUPS[2][2])


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


def _place_layer_in_group(project, group, layer):
    node = project.layerTreeRoot().findLayer(layer.id())
    if node is not None and node.parent() == group:
        return node
    if node is None:
        return group.addLayer(layer)
    return _move_tree_node(node, group, len(group.children()))


def _move_tree_node(node, parent, index):
    """Keep a layer's tree presence continuous during registry synchronization."""
    old_parent = node.parent()
    if old_parent == parent:
        old_index = parent.children().index(node)
        if old_index == index:
            return node
        if old_index < index:
            index += 1
    replacement = node.clone()
    # QGIS queues project-layer deletion when the last tree node disappears.
    # Disabling the registry bridge does not suppress its tree-removal slots.
    # Match native drag/drop: insert the replacement before removing the old node.
    parent.insertChildNode(index, replacement)
    old_parent.removeChildNode(node)
    return replacement


def _setup_readiness(service_id, field_names, language):
    readiness = assess_source_schema(service_id, field_names)
    message = source_readiness_message(language, readiness)
    if readiness["status"] == "AVAILABLE" and service_id == "forest_centre_stand":
        return "AVAILABLE", tr(language, "source_setup_stand_unmapped"), readiness
    return readiness["status"], message, readiness


def _setup_layer_readiness(service_id, layer, language):
    geometry_error = source_layer_geometry_error(layer, service_id, language)
    if geometry_error:
        return "NOT_AVAILABLE", geometry_error["message"], {
            "status": "NOT_AVAILABLE", "reason_code": geometry_error["reason_code"],
            "missing_fields": [],
        }
    return _setup_readiness(service_id, provider_field_names(layer), language)


def _syke_id_notice(service_id, language):
    if service_id.startswith("syke_") and not syke_user_id():
        return tr(language, "syke_id_recommended")
    return ""


def _style_forest_source(layer, service_id):
    """Apply stable project colors to managed reference polygon layers."""
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
        "forest_centre_gridcell": {
            "style": "no",
            "outline_style": "solid",
            "outline_color": "0,100,0,255",
            "outline_width": "0.25",
            "outline_width_unit": "MM",
        },
        "syke_groundwater_areas": {
            "color": "95,175,220,95",
            "outline_color": "55,115,165,220",
            "outline_width": "0.35",
        },
        "syke_rantaviiva_polygon_river": {
            "color": "79,159,224,125",
            "outline_color": "55,115,165,235",
            "outline_width": "0.35",
        },
        "syke_rantaviiva_lake": {
            "color": "79,159,224,125",
            "outline_color": "55,115,165,235",
            "outline_width": "0.35",
        },
    }
    style = styles.get(service_id)
    if service_id in PROTECTED_SERVICE_IDS:
        style = {
            "color": "210,95,125,95",
            "outline_color": "155,55,85,220",
            "outline_width": "0.35",
        }
    if style is not None:
        layer.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple(style)))
    elif service_id == "syke_rantaviiva_line_river":
        layer.setRenderer(QgsSingleSymbolRenderer(QgsLineSymbol.createSimple({
            "line_color": "79,159,224,255", "line_width": "0.65",
        })))
    if service_id in DETAILED_REFERENCE_SERVICE_IDS:
        # QGIS minimumScale is the most zoomed-out visible scale. At smaller
        # denominators (closer zooms) these detailed WFS layers remain visible.
        # Include the boundary despite QGIS's minimum-scale comparison tolerance.
        layer.setMinimumScale(FOREST_MINIMUM_VISIBLE_SCALE + 1e-6)
        layer.setMaximumScale(0.0)
        layer.setScaleBasedVisibility(True)
    elif service_id == "forest_centre_gridcell":
        # QGIS 4.2 excludes an equal minimum scale with a comparison tolerance.
        # A one-millionth-denominator margin includes 1:300 at that tolerance.
        layer.setMinimumScale(GRID_MINIMUM_VISIBLE_SCALE + 1e-6)
        layer.setMaximumScale(0.0)
        layer.setScaleBasedVisibility(True)
    elif service_id.startswith("syke_rantaviiva_"):
        layer.setMinimumScale(FOREST_MINIMUM_VISIBLE_SCALE + 1e-6)
        layer.setMaximumScale(0.0)
        layer.setScaleBasedVisibility(True)


def _order_reference_layers(project, groups):
    """Restore managed child order while retaining user layers and check states."""
    for group_id, _key, service_ids in REFERENCE_GROUPS:
        group = groups[group_id]
        index = 0
        for service_id in service_ids:
            layer = _managed_layer(project, RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "service_id", service_id)
            if layer is None:
                continue
            node = _place_layer_in_group(project, group, layer)
            _move_tree_node(node, group, index)
            index += 1


def _setup_parcels(project, group, language):
    """Create/reconnect polygon boundaries and a separate labels-only point layer."""
    return [
        _setup_mml_layer(project, group, language, service_id, collection, name_key, geometry)
        for service_id, collection, name_key, geometry in (
            (MML_PARCEL_SERVICE_ID, MML_PARCEL_COLLECTION, "parcel_layer", Qgis.GeometryType.Polygon),
            (MML_IDENTIFIER_SERVICE_ID, MML_IDENTIFIER_COLLECTION, "property_identifier_layer", Qgis.GeometryType.Point),
        )
    ]


def _setup_mml_layer(project, group, language, service_id, collection, name_key, geometry):
    label = tr(language, name_key)
    uri = qgis_mml_uri(collection)
    layer = _managed_layer(project, RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "service_id", service_id)
    existing = layer is not None
    if existing:
        if not layer.isValid() or layer.source() != uri or layer.providerType() != "oapif":
            layer.setDataSource(uri, label, "oapif")
        layer.setName(label)
    else:
        layer = QgsVectorLayer(uri, label, "oapif")
    if not layer.isValid():
        return {"service_id": service_id, "status": "UNAVAILABLE", "message": tr(language, "mml_layer_unavailable", layer=label)}
    if (layer.geometryType() != geometry or not layer.crs().isValid()
            or (geometry == Qgis.GeometryType.Point and MML_PARCEL_LABEL_FIELD not in provider_field_names(layer))):
        return {"service_id": service_id, "status": "INVALID_LAYER", "message": tr(language, "mml_layer_schema_invalid", layer=label)}
    if geometry == Qgis.GeometryType.Polygon:
        layer.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple({
            "style": "no", "outline_style": "solid", "outline_color": "255,0,0,255",
            "outline_width": "1", "outline_width_unit": "MM",
        })))
        layer.setLabelsEnabled(False)
        layer.setLabeling(None)
    else:
        layer.setRenderer(QgsNullSymbolRenderer())
        text_format = QgsTextFormat()
        text_format.setFont(QFont("Arial"))
        text_format.setColor(QColor("red"))
        text_format.setSize(20)
        buffer = QgsTextBufferSettings()
        buffer.setEnabled(True)
        buffer.setSize(2)
        buffer.setSizeUnit(Qgis.RenderUnit.Millimeters)
        buffer.setColor(QColor("white"))
        buffer.setOpacity(1)
        buffer.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        buffer.setFillBufferInterior(False)
        text_format.setBuffer(buffer)
        labeling = QgsPalLayerSettings()
        labeling.fieldName = MML_PARCEL_LABEL_FIELD
        labeling.isExpression = False
        labeling.placement = Qgis.LabelPlacement.OverPoint
        labeling.setFormat(text_format)
        layer.setLabeling(QgsVectorLayerSimpleLabeling(labeling))
        layer.setLabelsEnabled(True)
    # Include the exact visibility boundary despite QGIS comparison tolerance.
    minimum_scale = (IDENTIFIER_MINIMUM_VISIBLE_SCALE
                     if service_id == MML_IDENTIFIER_SERVICE_ID else REFERENCE_MINIMUM_VISIBLE_SCALE)
    layer.setMinimumScale(minimum_scale + 1e-6)
    layer.setMaximumScale(0.0)
    layer.setScaleBasedVisibility(True)
    layer.setCustomProperty(RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "service_id", service_id)
    if not existing:
        project.addMapLayer(layer, False)
    _place_layer_in_group(project, group, layer)
    layer.triggerRepaint()
    return {"service_id": service_id, "status": "AVAILABLE", "message": ""}


def _localized_group(root, group_id, label):
    node = _managed_node(root, RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "group_id", group_id)
    if node is None:
        node = root.addGroup(label)
        node.setCustomProperty(RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "group_id", group_id)
    else:
        node.setName(label)
    return node


def ensure_group_order(project, language):
    root = project.layerTreeRoot()
    groups = []
    for group_id, label_key in GROUP_IDS:
        groups.append(_localized_group(root, group_id, tr(language, label_key)))
    for index, group_id in enumerate(("results", "references", "basemaps")):
        current = _managed_node(root, RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "group_id", group_id)
        _move_tree_node(current, root, index)
    # A custom order can override tree order. Reset it to the layer-tree order
    # so the visible tree and map rendering follow the same documented stack.
    root.setHasCustomLayerOrder(False)
    root.setCustomLayerOrder(root.layerOrder())
    return {
        group_id: _managed_node(root, RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "group_id", group_id)
        for group_id, _label_key in GROUP_IDS
    }


def _reference_groups(project, references, language):
    for group_id, key, _service_ids in REFERENCE_GROUPS:
        _localized_group(references, group_id, tr(language, key))
    for index, (group_id, _key, _service_ids) in enumerate(REFERENCE_GROUPS):
        group = _managed_node(references, RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "group_id", group_id)
        _move_tree_node(group, references, index)
    return {
        group_id: _managed_node(references, RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "group_id", group_id)
        for group_id, _key, _service_ids in REFERENCE_GROUPS
    }


def results_group(project, language):
    """Return the existing results group, creating only that group if needed."""
    root = project.layerTreeRoot()
    group = _managed_node(root, RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "group_id", "results")
    if group is None:
        group = root.addGroup(tr(language, "results_group"))
        group.setCustomProperty(RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "group_id", "results")
    return group


def _add_or_relabel_wfs(project, group, service_id, language):
    definition = SERVICE_DEFINITIONS[service_id]
    label = tr(language, definition["name_key"])
    layer = _managed_layer(project, RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "service_id", service_id)
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
        configured_type = layer.customProperty(RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "feature_type", "")
        if configured_type and configured_type != metadata["feature_type"]:
            layer.setCustomProperty(RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "schema_changed_to", metadata["feature_type"])
            return layer, {
                "service_id": service_id,
                "status": "SCHEMA_CHANGED",
                "message": tr(language, "source_schema_changed", old=configured_type, new=metadata["feature_type"]),
                "metadata": metadata,
            }
        layer.setCustomProperty(RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "schema_changed_to", "")
        # Upgrade older managed connections without replacing the project layer
        # or losing user filters/authentication. Suppress the startup sample read
        # on reconnection as well as on newly created providers.
        uri = qgis_wfs_uri(metadata, layer.source())
        if uri != layer.source():
            layer.setDataSource(uri, label, "WFS")
            _style_forest_source(layer, service_id)
            if not layer.isValid():
                return layer, {"service_id": service_id, "status": "INVALID_LAYER",
                               "message": tr(language, "source_configured_invalid")}
        layer.setCustomProperty(RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "query_time", metadata["query_time"])
        layer.setCustomProperty(RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "schema_json", json.dumps(metadata["properties"], ensure_ascii=False))
        status, message, readiness = _setup_layer_readiness(service_id, layer, language)
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
    layer.setCustomProperty(RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "service_id", service_id)
    layer.setCustomProperty(RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "endpoint", metadata["endpoint"])
    layer.setCustomProperty(RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "feature_type", metadata["feature_type"])
    layer.setCustomProperty(RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "source_crs", metadata["source_crs"])
    layer.setCustomProperty(RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "query_time", metadata["query_time"])
    layer.setCustomProperty(RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "schema_json", json.dumps(metadata["properties"], ensure_ascii=False))
    project.addMapLayer(layer, False)
    _place_layer_in_group(project, group, layer)
    status, message, readiness = _setup_layer_readiness(service_id, layer, language)
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
            layer.customProperty(RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "layer_id", "") == RESULTS_LAYER_ID
            and layer.providerType() == "memory"
            and layer.featureCount() == 0
        ):
            project.removeMapLayer(layer.id())


def _ensure_osm(project, basemaps_group, language):
    layer = _managed_layer(project, RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "layer_id", OSM_LAYER_ID)
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
    layer.setCustomProperty(RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "layer_id", OSM_LAYER_ID)
    layer.setCustomProperty(RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "managed", True)
    project.addMapLayer(layer, False)
    basemaps_group.addLayer(layer)
    return layer


def _setup_basemaps(project, group, language):
    """Restore the stack, defaulting to topographic only when first introduced."""
    property_name = RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "layer_id"
    topographic_is_new = _managed_layer(project, property_name, "mml_maastokartta") is None
    layers = []
    statuses = []
    for layer_id, name_key, product, image_format in BASEMAPS:
        label = tr(language, name_key)
        uri = qgis_mml_wmts_uri(product, image_format)
        layer = _managed_layer(project, property_name, layer_id)
        existing = layer is not None
        if existing:
            if not layer.isValid() or layer.source() != uri:
                layer.setDataSource(uri, label, "wms")
            layer.setName(label)
        else:
            layer = QgsRasterLayer(uri, label, "wms")
        if not layer.isValid():
            statuses.append({"service_id": layer_id, "status": "INVALID_LAYER",
                             "error_code": "WMTS_LAYER_INVALID",
                             "message": tr(language, "basemap_unavailable", layer=label)})
            continue
        layer.setCustomProperty(property_name, layer_id)
        layer.setCustomProperty(RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "managed", True)
        if not existing:
            project.addMapLayer(layer, False)
        node = _place_layer_in_group(project, group, layer)
        if not existing:
            node.setItemVisibilityChecked(layer_id == "mml_maastokartta")
        layers.append(layer)
    osm = _ensure_osm(project, group, language)
    if osm is None:
        statuses.append({"service_id": OSM_LAYER_ID, "status": "INVALID_LAYER",
                         "error_code": "XYZ_LAYER_INVALID",
                         "message": tr(language, "basemap_unavailable", layer=tr(language, "osm_layer"))})
    else:
        layers.append(osm)
    topographic = next((layer for layer in layers
                        if layer.customProperty(property_name) == "mml_maastokartta"), None)
    for index, layer in enumerate(layers):
        node = _place_layer_in_group(project, group, layer)
        node = _move_tree_node(node, group, index)
        if topographic_is_new and topographic is not None:
            node.setItemVisibilityChecked(layer == topographic)
    if topographic_is_new and topographic is not None:
        group.setItemVisibilityChecked(True)
    return statuses


def setup_project(project=None, language="en"):
    """Create/reuse groups and configured online source layers.

    This operation does not process sources outside V1 scope.
    Failed source discovery is returned as coverage information for the UI.
    """
    project = project or QgsProject.instance()
    if not mml_api_key():
        return {
            "language": language, "ready": False, "groups": (), "out_of_scope": (),
            "sources": [{"service_id": MML_PARCEL_SERVICE_ID, "status": "UNAVAILABLE",
                         "error_code": "MML_API_KEY_REQUIRED", "message": tr(language, "mml_key_required")}],
        }
    groups = ensure_group_order(project, language)
    references = _reference_groups(project, groups["references"], language)
    statuses = _setup_parcels(project, references["properties"], language)
    for service_id in SERVICE_DEFINITIONS:
        group_id = next(group_id for group_id, _key, ids in REFERENCE_GROUPS if service_id in ids)
        layer, status = _add_or_relabel_wfs(project, references[group_id], service_id, language)
        statuses.append(status)
    _order_reference_layers(project, references)
    _remove_empty_results_placeholder(project)
    statuses.extend(_setup_basemaps(project, groups["basemaps"], language))
    source_statuses = {row["service_id"]: row["status"] for row in statuses}
    required_sources_ready = all(source_statuses.get(service_id) == "AVAILABLE" for service_id in (
        MML_PARCEL_SERVICE_ID, MML_IDENTIFIER_SERVICE_ID,
    )) and all(
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
