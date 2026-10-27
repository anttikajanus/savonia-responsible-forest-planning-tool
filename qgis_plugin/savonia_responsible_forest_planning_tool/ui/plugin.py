"""QGIS plugin lifecycle and thin toolbar/dock integration."""

import logging

from qgis.PyQt.QtCore import Qt, QUrl
from qgis.PyQt.QtGui import QAction, QDesktopServices
from qgis.PyQt.QtWidgets import QDockWidget, QInputDialog, QStyle
from qgis.core import QgsApplication, QgsProject, QgsSettings

from ..app_logging import LOGGER_NAME, configure_logging, record_business_action, shutdown_logging
from ..i18n import selected_language, tr
from .. import documentation
from ..processing import ResponsibleForestPlanningProcessingProvider
from ..adapters.project_setup import setup_project
from ..adapters.sources import SYKE_USER_ID_KEY, syke_user_id
from .wizard import ResponsibleForestPlanningWizard


logger = logging.getLogger(LOGGER_NAME + ".ui.plugin")


class ResponsibleForestPlanningPlugin:
    def __init__(self, iface, package_root=None):
        self.iface = iface
        self.package_root = package_root
        self.language = selected_language()
        self.toolbar = None
        self.wizard_action = None
        self.setup_action = None
        self.dock = None
        self.wizard = None
        self.processing_provider = None
        self.help_action = None
        self.about_action = None
        self.about_dialog = None

    def initGui(self):
        if self.toolbar is not None:
            return
        log_dir = configure_logging()
        logger.info("event=plugin_initialized log_directory=%s", log_dir or "unavailable")
        self.language = selected_language()
        self.toolbar = self.iface.addToolBar(tr(self.language, "toolbar_name"))
        self.toolbar.setObjectName("SavoniaForestPlanningToolbar")
        self.wizard_action = QAction(tr(self.language, "open_wizard"), self.iface.mainWindow())
        self.wizard_action.setIcon(
            self.iface.mainWindow().style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView)
        )
        self.wizard_action.setToolTip(tr(self.language, "tooltip_open_wizard"))
        self.wizard_action.setStatusTip(tr(self.language, "tooltip_open_wizard"))
        self.wizard_action.triggered.connect(self.show_wizard)
        self.setup_action = QAction(tr(self.language, "setup_project"), self.iface.mainWindow())
        self.setup_action.setIcon(
            self.iface.mainWindow().style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon)
        )
        self.setup_action.setToolTip(tr(self.language, "tooltip_setup_project"))
        self.setup_action.setStatusTip(tr(self.language, "tooltip_setup_project"))
        self.setup_action.triggered.connect(self.setup_project_layers)
        self.toolbar.addAction(self.wizard_action)
        self.iface.addPluginToMenu(tr(self.language, "toolbar_name"), self.wizard_action)
        self.iface.addPluginToMenu(tr(self.language, "toolbar_name"), self.setup_action)

        self.help_action = QAction(tr(self.language, "help_menu"), self.iface.mainWindow())
        self.help_action.setIcon(QgsApplication.getThemeIcon("/mActionHelpContents.svg"))
        self.help_action.setToolTip(tr(self.language, "tooltip_help"))
        self.help_action.setStatusTip(tr(self.language, "tooltip_help"))
        self.help_action.triggered.connect(self.show_help)
        self.about_action = QAction(tr(self.language, "about_menu"), self.iface.mainWindow())
        self.about_action.setIcon(self.iface.mainWindow().style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation))
        self.about_action.setToolTip(tr(self.language, "tooltip_about"))
        self.about_action.setStatusTip(tr(self.language, "tooltip_about"))
        self.about_action.triggered.connect(self.show_about)
        self.iface.pluginHelpMenu().addAction(self.help_action)
        self.iface.pluginHelpMenu().addAction(self.about_action)

        self.processing_provider = ResponsibleForestPlanningProcessingProvider()
        QgsApplication.processingRegistry().addProvider(self.processing_provider)
        self._ensure_dock()

    def show_help(self, *_args, section="workflow"):
        self._refresh_language()
        try:
            url = documentation.manual_url(self.language, section, self.package_root)
        except documentation.ResourceError as error:
            self._documentation_error(error)
            return
        self.open_documentation_url(url)

    def open_documentation_url(self, url):
        """Launch without network probing; the desktop browser owns online access."""
        try:
            opened = QDesktopServices.openUrl(QUrl(url))
        except Exception:
            logger.exception("event=documentation_browser_failed url=%s", url)
            opened = False
        if not opened:
            logger.warning("event=documentation_browser_failed url=%s", url)
            self.iface.messageBar().pushWarning(
                tr(self.language, "toolbar_name"), tr(self.language, "documentation_browser_error"))

    def _documentation_error(self, error):
        logger.warning("event=documentation_resource_failed resource=%s path=%s reason=%s",
                       error.resource, error.path, error.reason)
        self.iface.messageBar().pushWarning(
            tr(self.language, "toolbar_name"), tr(self.language, "documentation_resource_error"))

    def show_about(self, *_args):
        self._refresh_language()
        from .about import ResponsibleForestPlanningAboutDialog
        if self.about_dialog is None:
            try:
                self.about_dialog = ResponsibleForestPlanningAboutDialog(self, self.iface.mainWindow())
            except documentation.ResourceError as error:
                self._documentation_error(error)
                return
        self.about_dialog.show()
        self.about_dialog.raise_()

    def _ensure_dock(self):
        if self.dock is not None:
            return
        self.dock = QDockWidget(tr(self.language, "wizard_title"), self.iface.mainWindow())
        self.dock.setObjectName("SavoniaForestPlanningWizardDock")
        self.dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable
            | QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.wizard = ResponsibleForestPlanningWizard(self.iface, self.language)
        self.wizard.setup_requested.connect(self.setup_project_layers)
        self.wizard.help_requested.connect(self.show_help)
        self.wizard.about_requested.connect(self.show_about)
        self.dock.setWidget(self.wizard)
        self.iface.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock)
        self.dock.hide()

    def show_wizard(self):
        self._refresh_language()
        self._ensure_dock()
        self.dock.show()
        self.dock.raise_()
        self.dock.activateWindow()

    def _refresh_language(self):
        new_language = selected_language()
        if new_language == self.language:
            return
        old_menu = tr(self.language, "toolbar_name")
        self.language = new_language
        if self.wizard_action is not None:
            self.iface.removePluginMenu(old_menu, self.wizard_action)
            self.iface.removePluginMenu(old_menu, self.setup_action)
            self.wizard_action.setText(tr(self.language, "open_wizard"))
            self.wizard_action.setToolTip(tr(self.language, "tooltip_open_wizard"))
            self.wizard_action.setStatusTip(tr(self.language, "tooltip_open_wizard"))
            self.setup_action.setText(tr(self.language, "setup_project"))
            self.setup_action.setToolTip(tr(self.language, "tooltip_setup_project"))
            self.setup_action.setStatusTip(tr(self.language, "tooltip_setup_project"))
            self.iface.addPluginToMenu(tr(self.language, "toolbar_name"), self.wizard_action)
            self.iface.addPluginToMenu(tr(self.language, "toolbar_name"), self.setup_action)
            self.toolbar.setWindowTitle(tr(self.language, "toolbar_name"))
        for action, text, tooltip in (
            (self.help_action, "help_menu", "tooltip_help"),
            (self.about_action, "about_menu", "tooltip_about"),
        ):
            if action is not None:
                action.setText(tr(self.language, text))
                action.setToolTip(tr(self.language, tooltip))
                action.setStatusTip(tr(self.language, tooltip))
        if self.wizard is not None:
            self.wizard.set_language(self.language)
            self.dock.setWindowTitle(tr(self.language, "wizard_title"))
        if self.about_dialog is not None:
            self.about_dialog.set_language(self.language)
        if self.processing_provider is not None:
            QgsApplication.processingRegistry().removeProvider(self.processing_provider)
            self.processing_provider = ResponsibleForestPlanningProcessingProvider()
            QgsApplication.processingRegistry().addProvider(self.processing_provider)

    def setup_project_layers(self):
        self._refresh_language()
        if not syke_user_id():
            identifier, accepted = QInputDialog.getText(
                self.iface.mainWindow(),
                tr(self.language, "syke_id_title"),
                tr(self.language, "syke_id_prompt"),
            )
            if accepted and identifier.strip():
                QgsSettings().setValue(SYKE_USER_ID_KEY, identifier.strip())
        record_business_action("project_setup_started")
        logger.info("event=project_setup_started")
        try:
            result = setup_project(QgsProject.instance(), self.language)
        except Exception as exc:
            record_business_action(
                "project_setup_failed", error_type=type(exc).__name__
            )
            logger.exception(
                "event=project_setup_failed error_type=%s", type(exc).__name__
            )
            self.iface.messageBar().pushCritical(
                tr(self.language, "toolbar_name"),
                tr(self.language, "setup_error", error=type(exc).__name__),
            )
            return
        status_counts = {}
        for source in result["sources"]:
            status = source.get("status", "UNKNOWN")
            status_counts[status] = status_counts.get(status, 0) + 1
        notices = [
            "{0}: {1}".format(item["service_id"], item.get("message", item["status"]))
            for item in result["sources"]
            if item.get("status") not in ("AVAILABLE", "CONFIGURED") or item.get("message")
        ]
        if not result.get("ready", True):
            blocking_notices = [
                "{0}: {1}".format(item["service_id"], item.get("message", item["status"]))
                for item in result["sources"]
                if item.get("status") not in ("AVAILABLE", "CONFIGURED")
            ]
            record_business_action(
                "project_setup_failed", error_type="REQUIRED_SOURCE_NOT_READY"
            )
            logger.warning(
                "event=project_setup_failed error_type=REQUIRED_SOURCE_NOT_READY "
                "source_status_counts=%s", status_counts,
            )
            self.iface.messageBar().pushCritical(
                tr(self.language, "toolbar_name"),
                tr(self.language, "setup_not_ready", details="; ".join(blocking_notices)),
            )
            return
        record_business_action(
            "project_setup_completed",
            source_count=len(result["sources"]),
            source_status_counts=status_counts,
        )
        logger.info(
            "event=project_setup_completed source_count=%d source_status_counts=%s",
            len(result["sources"]), status_counts,
        )
        if notices:
            self.iface.messageBar().pushWarning(
                tr(self.language, "toolbar_name"),
                tr(self.language, "setup_attention", details="; ".join(notices)),
            )
        else:
            self.iface.messageBar().pushSuccess(
                tr(self.language, "toolbar_name"), tr(self.language, "setup_done")
            )

    def unload(self):
        for action in (self.help_action, self.about_action):
            if action is not None:
                self.iface.pluginHelpMenu().removeAction(action)
                action.deleteLater()
        self.help_action = self.about_action = None
        if self.about_dialog is not None:
            self.about_dialog.close()
            self.about_dialog.deleteLater()
            self.about_dialog = None
        if self.wizard_action is not None:
            self.iface.removePluginMenu(tr(self.language, "toolbar_name"), self.wizard_action)
            self.wizard_action.deleteLater()
            self.wizard_action = None
        if self.setup_action is not None:
            self.iface.removePluginMenu(tr(self.language, "toolbar_name"), self.setup_action)
            self.setup_action.deleteLater()
            self.setup_action = None
        if self.toolbar is not None:
            self.iface.mainWindow().removeToolBar(self.toolbar)
            self.toolbar.deleteLater()
            self.toolbar = None
        if self.processing_provider is not None:
            QgsApplication.processingRegistry().removeProvider(self.processing_provider)
            self.processing_provider = None
        if self.dock is not None:
            self.dock.close()
            self.iface.removeDockWidget(self.dock)
            self.dock.deleteLater()
            self.dock = None
            self.wizard = None
        logger.info("event=plugin_unloaded")
        shutdown_logging()
