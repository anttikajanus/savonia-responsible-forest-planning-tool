"""Build the QGIS result layer from normalized classified-piece rows."""

import json

from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    Qgis, QgsAttributeEditorContainer, QgsAttributeEditorField,
    QgsAttributeEditorTextElement, QgsEditorWidgetSetup, QgsFeature, QgsField,
    QgsGeometry, QgsVectorLayer,
)

from ..analysis.classification import CRITERION_FIELDS, TIERS
from ..analysis.domain import METRIC_FIELDS, METRIC_GROUPS
from ..analysis.grid_indicators import AGE_METRICS
from ..i18n import tr
from .provider_utils import require_provider_success
from .result_precision import RESULT_DECIMALS, published_value
from .serialization import json_default


def create_classified_result_layer(rows, language="en"):
    """Create the existing EPSG:3067 result layer from classified rows."""
    layer = QgsVectorLayer("MultiPolygon?crs=EPSG:3067", "classified_forest_polygons", "memory")
    fields = [
        QgsField("source_stand_id", QVariant.String, len=128),
        QgsField("class_all_out", QVariant.String, len=16),
        QgsField("class_bau", QVariant.String, len=16),
        QgsField("class_light", QVariant.String, len=16),
        QgsField("class_balance", QVariant.String, len=16),
        QgsField("class_protection", QVariant.String, len=16),
        QgsField("class_superprotection", QVariant.String, len=16),
        *(QgsField(field, QVariant.String, len=16) for field, _, _ in CRITERION_FIELDS),
        QgsField("stand_has_overlap", QVariant.Bool),
        QgsField("area_ha", QVariant.Double),
    ]
    fields.extend([
        QgsField(name, QVariant.Int if name in AGE_METRICS else QVariant.Double)
        for name in METRIC_FIELDS
    ])
    fields.extend([
        QgsField("indicator_coverage", QVariant.String),
        QgsField("tier_rule_ids", QVariant.String),
        QgsField("source_ids", QVariant.String),
        QgsField("section10_stand_promoted", QVariant.Bool),
        QgsField("programme_info", QVariant.String, len=8192),
        QgsField("programme_protected_overlap", QVariant.String, len=16),
    ])
    require_provider_success(layer.dataProvider().addAttributes(fields), "classified result fields")
    layer.updateFields()
    for name in (*METRIC_FIELDS, "area_ha"):
        index = layer.fields().indexFromName(name)
        layer.setFieldAlias(index, tr(language, "metric_" + name))
        if name not in AGE_METRICS:
            layer.setEditorWidgetSetup(index, QgsEditorWidgetSetup("Range", {
                "Precision": RESULT_DECIMALS.get(name, 2), "AllowNull": True,
            }))
    for field, _, _ in CRITERION_FIELDS:
        index = layer.fields().indexFromName(field)
        layer.setFieldAlias(index, tr(language, field))
        layer.setEditorWidgetSetup(index, QgsEditorWidgetSetup("ValueMap", {"map": [
            {tr(language, "criterion_match"): "MATCH"},
            {tr(language, "criterion_no_match"): "NO_MATCH"},
            {tr(language, "criterion_unknown"): "UNKNOWN"},
        ]}))
    _configure_result_form(layer, language)
    layer.setFieldAlias(layer.fields().indexFromName("stand_has_overlap"), tr(language, "field_stand_has_overlap"))

    features = []
    for row in rows:
        feature = QgsFeature(layer.fields())
        geometry = QgsGeometry(row["geometry"])
        geometry.convertToMultiType()
        feature.setGeometry(geometry)
        attributes = [row["source_stand_id"]]
        attributes.extend(row["classes"][tier] for tier, _label in TIERS)
        attributes.extend(row[field] for field, _, _ in CRITERION_FIELDS)
        attributes.append(row.get("stand_has_overlap", False))
        attributes.append(published_value("area_ha", row["area_ha"]))
        attributes.extend(published_value(name, row["indicators"].get(name)) for name in METRIC_FIELDS)
        attributes.extend([
            json.dumps(row.get("indicator_coverage", {}), sort_keys=True, default=json_default),
            json.dumps(row["rules"], sort_keys=True, default=json_default),
            json.dumps(row["source_ids"], sort_keys=True, default=json_default),
            row["section10_stand_promoted"],
            json.dumps(row["programme_info"], ensure_ascii=False, sort_keys=True, default=json_default),
            row["programme_protected_overlap"],
        ])
        feature.setAttributes(attributes)
        features.append(feature)
    require_provider_success(layer.dataProvider().addFeatures(features), "classified result features")
    layer.updateExtents()
    return layer


def create_water_evidence_layer(evidence, language="en"):
    """Create the single combined buffered-water evidence layer for a run."""
    layer = QgsVectorLayer("MultiPolygon?crs=EPSG:3067", tr(language, "water_evidence_layer"), "memory")
    fields = [
        QgsField("evidence_id", QVariant.String, len=64),
        QgsField("source_refs", QVariant.String),
        QgsField("source_update_dates", QVariant.String),
        QgsField("buffer_distance_m", QVariant.Double),
        QgsField("source_retrieved_feature_count", QVariant.Int),
        QgsField("buffers_generated_count", QVariant.Int),
        QgsField("aoi_contributing_buffer_feature_count", QVariant.Int),
    ]
    require_provider_success(layer.dataProvider().addAttributes(fields), "buffered water evidence fields")
    layer.updateFields()
    aliases = {
        "evidence_id": "water_evidence_id",
        "source_refs": "water_source_refs",
        "source_update_dates": "water_source_update_dates",
        "buffer_distance_m": "water_buffer_distance",
        "source_retrieved_feature_count": "water_source_retrieved_count",
        "buffers_generated_count": "water_buffers_generated_count",
        "aoi_contributing_buffer_feature_count": "water_aoi_contributing_count",
    }
    for field_name, label_key in aliases.items():
        layer.setFieldAlias(layer.fields().indexFromName(field_name), tr(language, label_key))
    geometry = evidence.get("geometry")
    if geometry is not None and not geometry.isNull() and not geometry.isEmpty():
        feature = QgsFeature(layer.fields())
        geometry = QgsGeometry(geometry)
        geometry.convertToMultiType()
        feature.setGeometry(geometry)
        feature.setAttributes([
            "combined_riparian_buffer",
            json.dumps(evidence.get("source_refs", ()), ensure_ascii=False, sort_keys=True),
            json.dumps(evidence.get("source_update_dates", ()), ensure_ascii=False, sort_keys=True, default=json_default),
            evidence.get("buffer_distance_m"),
            evidence.get("source_retrieved_feature_count", 0),
            evidence.get("buffers_generated_count", 0),
            evidence.get("aoi_contributing_buffer_feature_count", 0),
        ])
        require_provider_success(layer.dataProvider().addFeatures([feature]), "buffered water evidence feature")
    layer.updateExtents()
    return layer


def _configure_result_form(layer, language):
    """Offer the same field order in a grouped form, persisted by the writer."""
    config = layer.editFormConfig()
    config.setLayout(Qgis.AttributeFormLayout.DragAndDrop)
    root = config.invisibleRootContainer()
    root.clear()
    fields = layer.fields()
    result_fields = ("source_stand_id", *("class_" + tier for tier, _ in TIERS),
                     *(field for field, _, _ in CRITERION_FIELDS), "stand_has_overlap", "area_ha")
    metric_fields = set(METRIC_FIELDS) | set(result_fields)
    provenance = tuple(field.name() for field in fields if field.name() not in metric_fields)
    for group_id, names in (("result", result_fields), *METRIC_GROUPS, ("provenance", provenance)):
        group = QgsAttributeEditorContainer(tr(language, "field_group_" + group_id), root)
        group.setType(Qgis.AttributeEditorContainerType.Tab)
        if group_id in ("result", "stand"):
            note = QgsAttributeEditorTextElement("area_definitions", group)
            note.setShowLabel(False)
            note.setText(tr(language, "note_area_definitions"))
            group.addChildElement(note)
        for name in names:
            group.addChildElement(QgsAttributeEditorField(name, fields.indexFromName(name), group))
        root.addChildElement(group)
    layer.setEditFormConfig(config)
