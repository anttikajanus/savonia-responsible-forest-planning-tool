"""Plugin-owned technical diagnostics and separate business-action records."""

import copy
import json
import logging
import os
import time
from logging.handlers import RotatingFileHandler

from qgis.core import Qgis, QgsApplication, QgsMessageLog


LOG_DIRECTORY_NAME = "savonia_responsible_forest_planning_tool"
PLUGIN_TAG = "Savonia - Responsible Forest Planning"
LOGGER_NAME = "savonia_responsible_forest_planning_tool"
BUSINESS_LOGGER_NAME = "savonia_responsible_forest_planning.business_actions"
MAX_LOG_BYTES = 2 * 1024 * 1024
BACKUP_COUNT = 3


class _UtcFormatter(logging.Formatter):
    converter = time.gmtime


class _QgisMessageHandler(logging.Handler):
    """Forward selected Python records to QGIS's Log Messages panel."""

    def emit(self, record):
        try:
            if record.levelno >= logging.ERROR:
                level = Qgis.MessageLevel.Critical
            elif record.levelno >= logging.WARNING:
                level = Qgis.MessageLevel.Warning
            else:
                level = Qgis.MessageLevel.Info
            panel_record = copy.copy(record)
            panel_record.exc_info = None
            panel_record.exc_text = None
            QgsMessageLog.logMessage(
                self.format(panel_record), PLUGIN_TAG, level, notifyUser=False
            )
        except Exception:
            # Logging must never mask the application operation being diagnosed.
            self.handleError(record)


class _BusinessActionFormatter(_UtcFormatter):
    """Serialize action events as one UTF-8 JSON object per line."""

    def format(self, record):
        payload = {
            "timestamp_utc": self.formatTime(record, "%Y-%m-%dT%H:%M:%S")
            + ".{0:03d}Z".format(int(record.msecs)),
            "event": record.event,
        }
        payload.update(record.attributes)
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)


_owned_handlers = []
_technical_logger = logging.getLogger(LOGGER_NAME)
_business_logger = logging.getLogger(BUSINESS_LOGGER_NAME)


def _remove_owned_handlers():
    for logger in (_technical_logger, _business_logger):
        for handler in tuple(logger.handlers):
            if handler in _owned_handlers:
                logger.removeHandler(handler)
                handler.close()
    _owned_handlers.clear()


def configure_logging():
    """Install bounded handlers under the QGIS per-user settings directory."""
    _remove_owned_handlers()
    _technical_logger.setLevel(logging.DEBUG)
    _technical_logger.propagate = False
    _business_logger.setLevel(logging.INFO)
    _business_logger.propagate = False

    qgis_handler = _QgisMessageHandler()
    qgis_handler.setLevel(logging.INFO)
    qgis_handler.setFormatter(_UtcFormatter("%(levelname)s %(message)s"))
    _technical_logger.addHandler(qgis_handler)
    _owned_handlers.append(qgis_handler)

    settings_dir = QgsApplication.qgisSettingsDirPath()
    log_dir = os.path.join(
        settings_dir, LOG_DIRECTORY_NAME, "logs"
    )
    try:
        os.makedirs(log_dir, exist_ok=True)
    except OSError as exc:
        _technical_logger.warning(
            "event=logging_file_unavailable error_type=%s", type(exc).__name__
        )
        return None

    technical_formatter = _UtcFormatter(
        "%(asctime)sZ %(levelname)s %(name)s %(message)s", "%Y-%m-%dT%H:%M:%S"
    )
    try:
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, "technical.log"),
            maxBytes=MAX_LOG_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(technical_formatter)
        _technical_logger.addHandler(file_handler)
        _owned_handlers.append(file_handler)
    except OSError as exc:
        _technical_logger.warning(
            "event=technical_log_file_unavailable error_type=%s", type(exc).__name__
        )

    try:
        business_handler = RotatingFileHandler(
            os.path.join(log_dir, "business-actions.jsonl"),
            maxBytes=MAX_LOG_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        business_handler.setLevel(logging.INFO)
        business_handler.setFormatter(_BusinessActionFormatter())
        _business_logger.addHandler(business_handler)
        _owned_handlers.append(business_handler)
    except OSError as exc:
        _technical_logger.warning(
            "event=business_action_log_unavailable error_type=%s", type(exc).__name__
        )
    return log_dir


def shutdown_logging():
    """Close only handlers created by this plugin."""
    _remove_owned_handlers()


def record_business_action(event, **attributes):
    """Write a compact operational event to the separate business-action log."""
    if _business_logger.handlers:
        _business_logger.info(
            "business action", extra={"event": event, "attributes": attributes}
        )

