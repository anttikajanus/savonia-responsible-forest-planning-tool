"""Worker-owned QGIS inputs for background wizard analyses."""

import logging

from qgis.core import (
    QgsCoordinateTransformContext, QgsFeature, QgsGeometry,
    QgsProcessingFeedback, QgsTask, QgsVectorLayer,
)

from .. import RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX
from ..app_logging import LOGGER_NAME
from ..adapters.sources import restrict_wfs_uri_to_request_bbox
from ..i18n import tr
from .workflow import run_workflow


logger = logging.getLogger(LOGGER_NAME + ".analysis.worker_task")

SOURCE_LAYER_PROPERTIES = (
    RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "endpoint",
    RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "feature_type",
    RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "schema_changed_to",
    RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "schema_json",
    RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "query_time",
    RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "source_crs",
)


def capture_worker_inputs(aoi, sources, selected_only, transform_context,
                          language, output_folder, output_name=None):
    """Copy wizard inputs to Python/QGIS value data on the UI thread.

    No layer or project QObject is retained by the returned structure. Source
    URIs can contain authentication references, so callers must not log them.
    """
    if aoi is None or not aoi.isValid():
        raise ValueError(tr(language, "error_aoi_layer"))
    source_features = list(
        aoi.getSelectedFeatures() if selected_only else aoi.getFeatures()
    )
    aoi_features = tuple(
        (feature.id(), bytes(feature.geometry().asWkb()))
        for feature in source_features
    )
    selected_source_feature_snapshots = {}
    if selected_only:
        for service_id, layer in sources.items():
            if layer is not None and (layer is aoi or layer.id() == aoi.id()):
                selected_source_feature_snapshots[service_id] = tuple(
                    (
                        feature.id(),
                        bytes(feature.geometry().asWkb()),
                        tuple(feature.attributes()),
                    )
                    for feature in source_features
                )
    copied_sources = {}
    for service_id, layer in sources.items():
        if layer is None:
            copied_sources[service_id] = None
            continue
        source_provider_type = str(layer.providerType())
        source_uri = str(layer.source())
        if source_provider_type.lower() == "wfs":
            source_uri = restrict_wfs_uri_to_request_bbox(source_uri)
        copied_sources[service_id] = {
            "uri": source_uri,
            "name": str(layer.name()),
            "provider": source_provider_type,
            "properties": {
                key: str(layer.customProperty(key, "") or "")
                for key in SOURCE_LAYER_PROPERTIES
            },
        }
    return {
        "aoi": {
            "name": str(aoi.name()),
            "crs": str(aoi.crs().authid()),
            "features": aoi_features,
        },
        "sources": copied_sources,
        "selected_source_feature_snapshots": selected_source_feature_snapshots,
        "transform_context": QgsCoordinateTransformContext(transform_context),
        "language": str(language),
        "output_folder": str(output_folder),
        "output_name": str(output_name or ""),
    }


class _TaskFeedback(QgsProcessingFeedback):
    """Processing feedback that relays progress while polling task cancel."""

    def __init__(self, task):
        super().__init__()
        self._task = task

    def isCanceled(self):
        return self._task.cancellation_requested() or super().isCanceled()

    def setProgress(self, progress):
        super().setProgress(progress)
        self._task.setProgress(progress)

    def setProgressText(self, text):
        super().setProgressText(text)
        self._task.setDescription(str(text))

    def pushInfo(self, info):
        super().pushInfo(info)
        logger.info("wizard_feedback %s", str(info).replace("\n", " "))


class ResponsibleForestPlanningAnalysisTask(QgsTask):
    """Build QGIS layers in the worker, then call the shared workflow."""

    def __init__(self, description, worker_inputs, completion_callback):
        super().__init__(description, QgsTask.CanCancel)
        self._worker_inputs = worker_inputs
        self._completion_callback = completion_callback
        self.result = None
        self.error = None

    def cancellation_requested(self):
        """Expose QgsTask's protected cancellation state to worker feedback."""
        return self.isCanceled()

    @staticmethod
    def _construct_aoi(snapshot, language):
        layer = QgsVectorLayer(
            "MultiPolygon?crs={0}".format(snapshot["crs"]),
            snapshot["name"], "memory",
        )
        if not layer.isValid():
            raise RuntimeError(tr(language, "error_aoi_layer"))
        features = []
        for feature_id, wkb in snapshot["features"]:
            feature = QgsFeature(layer.fields())
            feature.setId(feature_id)
            geometry = QgsGeometry()
            geometry.fromWkb(wkb)
            if geometry.isNull():
                raise RuntimeError(tr(language, "error_aoi_invalid", feature_id=feature_id))
            geometry.convertToMultiType()
            feature.setGeometry(geometry)
            features.append(feature)
        if features and not layer.dataProvider().addFeatures(features)[0]:
            raise RuntimeError(tr(language, "error_aoi_layer"))
        layer.updateExtents()
        return layer

    @staticmethod
    def _construct_sources(source_snapshots):
        layers = {}
        for service_id, snapshot in source_snapshots.items():
            if snapshot is None:
                layers[service_id] = None
                continue
            source_uri = snapshot["uri"]
            if snapshot["provider"].lower() == "wfs":
                source_uri = restrict_wfs_uri_to_request_bbox(source_uri)
            layer = QgsVectorLayer(source_uri, snapshot["name"], snapshot["provider"])
            for key, value in snapshot["properties"].items():
                layer.setCustomProperty(key, value)
            layers[service_id] = layer
        return layers

    def run(self):
        try:
            aoi_layer = self._construct_aoi(
                self._worker_inputs["aoi"], self._worker_inputs["language"],
            )
            sources = self._construct_sources(self._worker_inputs["sources"])
            feedback = _TaskFeedback(self)
            self.result = run_workflow({
                "transform_context": self._worker_inputs["transform_context"],
                "language": self._worker_inputs["language"],
                "aoi_layer": aoi_layer,
                # QGIS selections are main-thread state; use captured feature snapshots
                # instead of querying the source layers from this worker.
                "selected_only": False,
                "selected_source_feature_snapshots": self._worker_inputs[
                    "selected_source_feature_snapshots"
                ],
                "sources": sources,
                "output_folder": self._worker_inputs["output_folder"],
                "output_name": self._worker_inputs["output_name"] or None,
                "entry_point": "wizard",
            }, feedback)
            return True
        except Exception as exc:
            self.error = exc
            logger.exception("wizard_task_failed error_type=%s", type(exc).__name__)
            return False

    def finished(self, successful):
        """QGIS invokes this on the main thread after run() returns."""
        self._completion_callback(self, successful)
