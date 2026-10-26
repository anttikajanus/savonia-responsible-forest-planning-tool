"""Shared QGIS helpers used by workflow steps."""

from qgis.core import Qgis, QgsCoordinateReferenceSystem, QgsProcessingException

from ...i18n import tr

TARGET_CRS = QgsCoordinateReferenceSystem("EPSG:3067")


def _apply_coordinate_transform(geometry, transform):
    result = geometry.transform(transform)
    if result != Qgis.GeometryOperationResult.Success:
        raise RuntimeError("coordinate transformation returned {0}".format(result))


def _feedback(feedback, method, message):
    if feedback is not None and hasattr(feedback, method):
        getattr(feedback, method)(message)


def _check_cancelled(feedback, language="en"):
    if feedback is not None and feedback.isCanceled():
        raise QgsProcessingException(tr(language, "error_cancelled"))


