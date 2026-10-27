"""Write analysis and provenance layers to a GeoPackage."""

import os

from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsField, QgsMapLayer, QgsMapLayerStyle, QgsVectorFileWriter, QgsVectorLayer, QgsFeature

from .provider_utils import require_provider_success
from .serialization import stringify


def _write_layer(layer, path, layer_name, transform_context, first_layer=False):
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    options.layerName = layer_name
    options.fileEncoding = "UTF-8"
    options.actionOnExistingFile = (
        QgsVectorFileWriter.CreateOrOverwriteFile if first_layer
        else QgsVectorFileWriter.CreateOrOverwriteLayer
    )
    result = QgsVectorFileWriter.writeAsVectorFormatV3(
        layer, path, transform_context, options
    )
    if result[0] != QgsVectorFileWriter.NoError:
        raise IOError("Could not write GeoPackage layer {0}: {1}".format(layer_name, result[1]))

def write_geopackage(path, result_layer, snapshots, coverage, run_metadata, transform_context):
    """Write one analysis result layer plus non-result source/provenance layers."""
    if os.path.exists(path):
        os.remove(path)
    _write_layer(result_layer, path, "classified_forest_polygons", transform_context, first_layer=True)
    first = False
    for layer_name, layer in snapshots:
        _write_layer(layer, path, layer_name, transform_context, first_layer=first)
        first = False
    coverage_layer = _table_layer("source_coverage", coverage)
    _write_layer(coverage_layer, path, "source_coverage", transform_context, first_layer=first)
    metadata_layer = _table_layer("run_metadata", run_metadata)
    _write_layer(metadata_layer, path, "run_metadata", transform_context, first_layer=False)
    _save_result_presentation(path, result_layer)
    return path


def _save_result_presentation(path, result_layer):
    """Keep field aliases and numeric display settings when reopening the file."""
    saved = QgsVectorLayer(path + "|layername=classified_forest_polygons", "classified_forest_polygons", "ogr")
    if not saved.isValid():
        raise IOError("Could not reopen GeoPackage result layer to save field presentation")
    style = QgsMapLayerStyle()
    style.readFromLayer(result_layer)
    style.writeToLayer(saved)
    result, message = saved.saveStyleToDatabaseV2(
        "classified_forest_polygons", "", True, "",
        QgsMapLayer.Fields | QgsMapLayer.Forms,
    )
    if result != QgsMapLayer.SaveStyleResult.Success:
        raise IOError("Could not save GeoPackage result field presentation: {0}".format(message))


def _table_layer(name, rows):
    layer = QgsVectorLayer("None", name, "memory")
    keys = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    data_provider = layer.dataProvider()
    require_provider_success(
        data_provider.addAttributes([QgsField(key, QVariant.String) for key in keys]),
        "{0} table fields".format(name),
    )
    layer.updateFields()
    features = []
    for row in rows:
        feature = QgsFeature(layer.fields())
        feature.setAttributes([stringify(row.get(key)) for key in keys])
        features.append(feature)
    require_provider_success(data_provider.addFeatures(features), "{0} table features".format(name))
    layer.updateExtents()
    return layer

