"""Persistent dock contents and polygon drawing tool."""

import os
import math
import sys

from qgis.PyQt import sip
from qgis.PyQt.QtCore import QLocale, QStandardPaths, Qt, pyqtSignal
from qgis.PyQt.QtGui import QColor, QDoubleValidator, QValidator
from qgis.PyQt.QtWidgets import (
    QButtonGroup, QCheckBox, QFileDialog, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QRadioButton, QStackedWidget, QStyle,
    QToolBar, QVBoxLayout, QWidget,
)
from qgis.core import (
    Qgis, QgsApplication, QgsFeature, QgsFillSymbol, QgsGeometry,
    QgsMapLayerProxyModel, QgsProject, QgsSettings,
    QgsSingleSymbolRenderer, QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.gui import QgsMapLayerComboBox, QgsMapTool, QgsRubberBand

from .. import RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX
from ..analysis.classification import TIERS
from ..analysis.worker_task import ResponsibleForestPlanningAnalysisTask, capture_worker_inputs
from ..adapters.sources import SERVICE_DEFINITIONS
from ..adapters.source_layers import verify_source_layer
from ..i18n import tr
from ..adapters.project_setup import results_group


OUTPUT_FOLDER_SETTING_KEY = "savonia-forest-planning/output-folder"
SAWLOG_PRICE_SETTING_KEY = "savonia-forest-planning/sawlog-price-eur-m3"


class PolygonDrawTool(QgsMapTool):
    def __init__(self, canvas, callback, language):
        super().__init__(canvas)
        self.canvas = canvas
        self.callback = callback
        self.language = language
        self.points = []
        self.previous_tool = canvas.mapTool()
        self.rubber_band = QgsRubberBand(canvas, QgsWkbTypes.PolygonGeometry)
        self.rubber_band.setColor(QColor(230, 100, 40, 180))
        self.rubber_band.setWidth(2)

    def canvasPressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            point = event.mapPoint()
            self.points.append(point)
            self.rubber_band.addPoint(point, True)
        elif event.button() == Qt.MouseButton.RightButton:
            self.finish()

    def canvasMoveEvent(self, event):
        if self.points:
            self.rubber_band.movePoint(event.mapPoint())

    def finish(self):
        if len(self.points) >= 3:
            geometry = QgsGeometry.fromPolygonXY([self.points])
            crs = self.canvas.mapSettings().destinationCrs()
            layer = QgsVectorLayer(
                "Polygon?crs={0}".format(crs.authid()),
                tr(self.language, "drawn_aoi_layer"), "memory",
            )
            feature = QgsFeature(layer.fields())
            feature.setGeometry(geometry)
            if not layer.dataProvider().addFeature(feature):
                raise RuntimeError(tr(self.language, "error_drawn_aoi_create"))
            layer.updateExtents()
            self.callback(layer)
        else:
            self.callback(None)
        self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
        self.canvas.setMapTool(self.previous_tool)

    def deactivate(self):
        self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
        super().deactivate()


class ResponsibleForestPlanningWizard(QWidget):
    setup_requested = pyqtSignal()
    help_requested = pyqtSignal()
    about_requested = pyqtSignal()

    def __init__(self, iface, language):
        super().__init__()
        self.iface = iface
        self.language = language
        self.drawn_aoi = None
        self.draw_tool = None
        self._selection_layer = None
        self._selection_choice_manually_set = False
        self._updating_selection_choice = False
        self._analysis_task = None
        self._analysis_cancel_requested = False
        self._layer_connections = []
        self._external_connections = []
        self._shutting_down = False
        self._build_ui()
        project = QgsProject.instance()
        for signal, callback in (
            (project.layersAdded, self._refresh_layer_connections),
            (project.layersWillBeRemoved, self._disconnect_layer_connections),
            (project.layersRemoved, self._refresh_layer_connections),
            (self.iface.mapCanvas().extentsChanged, self._update_buttons),
            (self.iface.mapCanvas().destinationCrsChanged, self._update_buttons),
        ):
            signal.connect(callback)
            self._external_connections.append((signal, callback))
        self._refresh_layer_connections()

    def _build_ui(self):
        root = QVBoxLayout(self)
        self.toolbar = QToolBar(self)
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(self.iface.iconSize(True))
        self.setup_action = self.toolbar.addAction(tr(self.language, "setup_project"))
        self.setup_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        self.setup_action.triggered.connect(self.setup_requested.emit)
        self.toolbar.addSeparator()
        self.redock_action = self.toolbar.addAction(tr(self.language, "redock_panel"))
        redock_icon = QgsApplication.getThemeIcon("/mDockify.svg")
        if redock_icon.isNull():
            redock_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarNormalButton)
        self.redock_action.setIcon(redock_icon)
        self.redock_action.setToolTip(tr(self.language, "tooltip_redock_panel"))
        self.redock_action.setStatusTip(tr(self.language, "tooltip_redock_panel"))
        self.redock_action.triggered.connect(self._redock_dock)
        self.help_action = self.toolbar.addAction(tr(self.language, "help"))
        self.help_action.setIcon(QgsApplication.getThemeIcon("/mActionHelpContents.svg"))
        self.help_action.triggered.connect(self.help_requested.emit)
        self.about_action = self.toolbar.addAction(tr(self.language, "about"))
        self.about_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation))
        self.about_action.triggered.connect(self.about_requested.emit)
        root.addWidget(self.toolbar)

        self.pages = QStackedWidget(self)
        root.addWidget(self.pages)

        area_page = QWidget(self)
        area_layout = QVBoxLayout(area_page)
        self.heading = QLabel(tr(self.language, "wizard_heading"), area_page)
        self.heading.setWordWrap(True)
        self.description = QLabel(tr(self.language, "wizard_description"), area_page)
        self.description.setWordWrap(True)
        area_layout.addWidget(self.heading)
        area_layout.addWidget(self.description)
        area_group = QGroupBox(tr(self.language, "analysis_area_group"), area_page)
        self.area_group = area_group
        area_group_layout = QVBoxLayout(area_group)
        self.aoi_mode_group = QButtonGroup(area_group)
        self.layer_mode = QRadioButton(tr(self.language, "aoi_mode_layer"), area_group)
        self.draw_mode = QRadioButton(tr(self.language, "aoi_mode_draw"), area_group)
        self.extent_mode = QRadioButton(tr(self.language, "aoi_mode_extent"), area_group)
        self.aoi_mode_group.addButton(self.layer_mode)
        self.aoi_mode_group.addButton(self.draw_mode)
        self.aoi_mode_group.addButton(self.extent_mode)
        self.layer_mode.setChecked(True)
        area_group_layout.addWidget(self.layer_mode)

        self.layer_controls = QWidget(area_group)
        layer_controls_layout = QVBoxLayout(self.layer_controls)
        layer_controls_layout.setContentsMargins(24, 0, 0, 6)
        self.aoi_layer_label = QLabel(tr(self.language, "aoi_layer_label"), self.layer_controls)
        layer_controls_layout.addWidget(self.aoi_layer_label)
        self.layer_combo = QgsMapLayerComboBox(self.layer_controls)
        self.layer_combo.setFilters(Qgis.LayerFilter.PolygonLayer)
        self.layer_combo.setAllowEmptyLayer(True, tr(self.language, "aoi_layer_placeholder"))
        self.layer_combo.setLayer(None)
        layer_controls_layout.addWidget(self.layer_combo)
        self.selected_only = QCheckBox(self.layer_controls)
        self.selected_only.setToolTip(tr(self.language, "selected_only_tooltip"))
        self.selected_only.toggled.connect(self._on_selected_only_toggled)
        layer_controls_layout.addWidget(self.selected_only)
        area_group_layout.addWidget(self.layer_controls)

        area_group_layout.addWidget(self.draw_mode)
        self.draw_controls = QWidget(area_group)
        draw_controls_layout = QVBoxLayout(self.draw_controls)
        draw_controls_layout.setContentsMargins(24, 0, 0, 6)
        draw_buttons = QHBoxLayout()
        self.draw_button = QPushButton(tr(self.language, "draw_aoi"), self.draw_controls)
        draw_icon = QgsApplication.getThemeIcon("/mActionCapturePolygon.svg")
        if draw_icon.isNull():
            draw_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder)
        self.draw_button.setIcon(draw_icon)
        self.draw_button.setToolTip(tr(self.language, "tooltip_draw_aoi"))
        self.draw_button.clicked.connect(self.start_drawing)
        self.clear_drawn_aoi_button = QPushButton(tr(self.language, "clear_drawn_aoi"), self.draw_controls)
        self.clear_drawn_aoi_button.setEnabled(False)
        self.clear_drawn_aoi_button.clicked.connect(self.clear_drawn_aoi)
        draw_buttons.addWidget(self.draw_button)
        draw_buttons.addWidget(self.clear_drawn_aoi_button)
        draw_controls_layout.addLayout(draw_buttons)
        area_group_layout.addWidget(self.draw_controls)
        area_group_layout.addWidget(self.extent_mode)
        self.aoi_status = QLabel("", area_group)
        self.aoi_status.setWordWrap(True)
        area_group_layout.addWidget(self.aoi_status)
        area_layout.addWidget(area_group)

        self.layer_mode.toggled.connect(self._update_aoi_mode)
        self.draw_mode.toggled.connect(self._update_aoi_mode)
        self.extent_mode.toggled.connect(self._update_aoi_mode)
        self.layer_combo.layerChanged.connect(self._on_aoi_layer_changed)
        self._on_aoi_layer_changed(self.layer_combo.currentLayer())
        self._update_aoi_mode()

        self.sawlog_price_label = QLabel(tr(self.language, "sawlog_price"), area_page)
        area_layout.addWidget(self.sawlog_price_label)
        self.sawlog_price = QLineEdit(area_page)
        self.sawlog_price_label.setBuddy(self.sawlog_price)
        self.price_validator = QDoubleValidator(0, sys.float_info.max, 2, self.sawlog_price)
        self.price_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.sawlog_price.setValidator(self.price_validator)
        self._set_price_locale()
        remembered_price = QgsSettings().value(SAWLOG_PRICE_SETTING_KEY)
        try:
            remembered_price = float(remembered_price)
            if math.isfinite(remembered_price) and remembered_price > 0 and round(remembered_price, 2) == remembered_price:
                self.sawlog_price.setText(self.price_validator.locale().toString(remembered_price, "f", 2))
        except (TypeError, ValueError, OverflowError):
            pass
        self.sawlog_price.textChanged.connect(self._price_changed)
        self.sawlog_price.editingFinished.connect(self._format_price)
        area_layout.addWidget(self.sawlog_price)

        self.output_folder_label = QLabel(tr(self.language, "output_folder"), area_page)
        area_layout.addWidget(self.output_folder_label)
        folder_row = QHBoxLayout()
        self.output_folder = QLineEdit(area_page)
        documents_folder = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation
        )
        remembered_folder = QgsSettings().value(OUTPUT_FOLDER_SETTING_KEY, documents_folder)
        self.output_folder.setText(str(remembered_folder or documents_folder))
        self.output_folder.editingFinished.connect(self._remember_output_folder)
        self.output_folder.textChanged.connect(self._update_buttons)
        browse_button = QPushButton("…", area_page)
        self.browse_button = browse_button
        browse_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        browse_button.setToolTip(tr(self.language, "tooltip_browse_output"))
        browse_button.setAccessibleName(tr(self.language, "output_folder"))
        browse_button.clicked.connect(self.choose_output_folder)
        folder_row.addWidget(self.output_folder)
        folder_row.addWidget(browse_button)
        area_layout.addLayout(folder_row)
        # Keep the form compact; spare dock height belongs below its controls.
        area_layout.addStretch()
        self.pages.addWidget(area_page)

        buttons = QHBoxLayout()
        self.previous_button = QPushButton(tr(self.language, "previous"), self)
        self.previous_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowLeft))
        self.previous_button.setToolTip(tr(self.language, "tooltip_previous"))
        self.next_button = QPushButton(tr(self.language, "next"), self)
        self.next_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowRight))
        self.next_button.setToolTip(tr(self.language, "tooltip_next"))
        self.run_button = QPushButton(tr(self.language, "run"), self)
        self.run_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        self.run_button.setToolTip(tr(self.language, "tooltip_run"))
        self.cancel_button = QPushButton(tr(self.language, "cancel_analysis"), self)
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_analysis)
        self.close_button = QPushButton(tr(self.language, "close"), self)
        self.close_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton))
        self.close_button.setToolTip(tr(self.language, "tooltip_close"))
        buttons.addWidget(self.previous_button)
        buttons.addWidget(self.next_button)
        buttons.addWidget(self.run_button)
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.close_button)
        root.addLayout(buttons)
        self.previous_button.clicked.connect(lambda: self.pages.setCurrentIndex(max(0, self.pages.currentIndex() - 1)))
        self.next_button.clicked.connect(lambda: self.pages.setCurrentIndex(min(self.pages.count() - 1, self.pages.currentIndex() + 1)))
        self.run_button.clicked.connect(self.run_analysis)
        self.close_button.clicked.connect(self._hide_dock)
        self.pages.currentChanged.connect(self._update_buttons)
        self.set_language(self.language)
        self._update_buttons()

    def set_language(self, language):
        """Refresh presentation in place; analysis callbacks and inputs stay intact."""
        self.language = language
        for widget, key in (
            (self.heading, "wizard_heading"), (self.description, "wizard_description"),
            (self.aoi_layer_label, "aoi_layer_label"),
            (self.sawlog_price_label, "sawlog_price"),
            (self.output_folder_label, "output_folder"),
            (self.layer_mode, "aoi_mode_layer"), (self.draw_mode, "aoi_mode_draw"),
            (self.extent_mode, "aoi_mode_extent"), (self.draw_button, "draw_aoi"),
            (self.clear_drawn_aoi_button, "clear_drawn_aoi"),
            (self.previous_button, "previous"), (self.next_button, "next"),
            (self.run_button, "run"), (self.close_button, "close"),
            (self.cancel_button, "canceling_analysis" if self._analysis_cancel_requested else "cancel_analysis"),
        ):
            widget.setText(tr(language, key))
            widget.setAccessibleName(tr(language, key))
        self.area_group.setTitle(tr(language, "analysis_area_group"))
        price = self._price_value()
        self._set_price_locale()
        if price is not None:
            self.sawlog_price.setText(self.price_validator.locale().toString(price, "f", 2))
        self.layer_combo.setAllowEmptyLayer(True, tr(language, "aoi_layer_placeholder"))
        selected_layer = self.layer_combo.currentLayer()
        self.selected_only.setText(tr(
            language, "selected_only_count",
            count=selected_layer.selectedFeatureCount() if selected_layer is not None else 0,
        ))
        self.browse_button.setAccessibleName(tr(language, "output_folder"))
        for action, key, tooltip in (
            (self.setup_action, "setup_project", "tooltip_setup_project"),
            (self.redock_action, "redock_panel", "tooltip_redock_panel"),
            (self.help_action, "help", "tooltip_help"),
            (self.about_action, "about", "tooltip_about"),
        ):
            action.setText(tr(language, key))
            action.setToolTip(tr(language, tooltip))
            action.setStatusTip(tr(language, tooltip))
            self.toolbar.widgetForAction(action).setAccessibleName(tr(language, key))
        for widget, tooltip in (
            (self.selected_only, "selected_only_tooltip"),
            (self.draw_button, "tooltip_draw_aoi"),
            (self.browse_button, "tooltip_browse_output"),
            (self.previous_button, "tooltip_previous"),
            (self.next_button, "tooltip_next"), (self.run_button, "tooltip_run"),
            (self.close_button, "tooltip_close"),
        ):
            widget.setToolTip(tr(language, tooltip))
        if self.draw_tool is not None:
            self.draw_tool.language = language
        if self.drawn_aoi is not None:
            self.drawn_aoi.setName(tr(language, "drawn_aoi_layer"))
        self._update_aoi_mode()
        if self.draw_tool is not None and self.iface.mapCanvas().mapTool() is self.draw_tool:
            self.aoi_status.setText(tr(language, "draw_instructions"))

    def _update_buttons(self, *_args):
        if not hasattr(self, "run_button"):
            return
        index = self.pages.currentIndex()
        has_multiple_pages = self.pages.count() > 1
        self.previous_button.setVisible(has_multiple_pages)
        self.next_button.setVisible(has_multiple_pages)
        self.previous_button.setEnabled(index > 0)
        self.next_button.setEnabled(index < self.pages.count() - 1)
        self.run_button.setEnabled(
            index == self.pages.count() - 1 and self._analysis_task is None and self._inputs_ready()
        )

    def _configured_sources(self):
        references = {
            layer.customProperty(RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "service_id", ""): layer
            for layer in QgsProject.instance().mapLayers().values()
            if layer.customProperty(RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "service_id", "")
        }
        return {service_id: references.get(service_id) for service_id in SERVICE_DEFINITIONS}

    def _inputs_ready(self):
        if self._shutting_down or self._price_value() is None:
            return False
        folder = self.output_folder.text().strip()
        if not folder:
            return False
        folder = os.path.abspath(folder)
        parent = folder if os.path.isdir(folder) else os.path.dirname(folder)
        if ((os.path.exists(folder) and not os.path.isdir(folder))
                or not os.path.isdir(parent) or not os.access(parent, os.W_OK)):
            return False
        if self.extent_mode.isChecked():
            canvas = self.iface.mapCanvas()
            extent = canvas.extent()
            if (not canvas.mapSettings().destinationCrs().isValid() or extent.isEmpty()
                    or not all(math.isfinite(value) for value in (extent.xMinimum(), extent.xMaximum(),
                                                                  extent.yMinimum(), extent.yMaximum()))):
                return False
        else:
            aoi = self.drawn_aoi if self.draw_mode.isChecked() else self.layer_combo.currentLayer()
            if (aoi is None or sip.isdeleted(aoi) or not aoi.isValid() or not aoi.crs().isValid()
                    or aoi.geometryType() != QgsWkbTypes.PolygonGeometry):
                return False
            if self.layer_mode.isChecked() and self.selected_only.isChecked():
                if aoi.selectedFeatureCount() == 0:
                    return False
            elif aoi.providerType().lower() != "wfs" and aoi.featureCount() <= 0:
                return False
        # Provider schema/identity is already local. Never request remote counts
        # or feature iteration merely to decide whether the form is complete.
        for service_id, layer in self._configured_sources().items():
            _, error = verify_source_layer(layer, service_id, self.language)
            if error or not layer.crs().isValid():
                return False
        return True

    @staticmethod
    def _disconnect_signals(connections):
        for signal, callback in connections:
            try:
                signal.disconnect(callback)
            except (TypeError, RuntimeError):
                # Project removal may already have destroyed a layer QObject.
                pass
        connections.clear()

    def _disconnect_layer_connections(self, *_args):
        self._disconnect_signals(self._layer_connections)

    def _refresh_layer_connections(self, *_args):
        self._disconnect_layer_connections()
        if self._shutting_down:
            return
        if self.drawn_aoi is not None and sip.isdeleted(self.drawn_aoi):
            self.drawn_aoi = None
            self.clear_drawn_aoi_button.setEnabled(False)
            if self.draw_mode.isChecked():
                self.aoi_status.setText(tr(self.language, "drawn_aoi_none"))
        for layer in QgsProject.instance().mapLayers().values():
            layer.customPropertyChanged.connect(self._refresh_layer_connections)
            self._layer_connections.append((layer.customPropertyChanged, self._refresh_layer_connections))
        layers = {layer.id(): layer for layer in self._configured_sources().values() if layer is not None}
        for layer in (self.layer_combo.currentLayer(), self.drawn_aoi):
            if layer is not None and not sip.isdeleted(layer):
                layers[layer.id()] = layer
        for layer in layers.values():
            for name in ("dataSourceChanged", "isValidChanged", "updatedFields", "crsChanged",
                         "featureAdded", "featureDeleted", "dataChanged"):
                signal = getattr(layer, name, None)
                if signal is not None:
                    signal.connect(self._update_buttons)
                    self._layer_connections.append((signal, self._update_buttons))
        self._update_buttons()

    def _set_price_locale(self):
        locale = QLocale("fi_FI" if self.language == "fi" else "en_US")
        locale.setNumberOptions(QLocale.NumberOption.RejectGroupSeparator | QLocale.NumberOption.OmitGroupSeparator)
        self.price_validator.setLocale(locale)

    def _price_value(self):
        text = self.sawlog_price.text().strip()
        state, _, _ = self.price_validator.validate(text, 0)
        value, valid = self.price_validator.locale().toDouble(text)
        return value if state == QValidator.State.Acceptable and valid and math.isfinite(value) and value > 0 else None

    def _price_changed(self, *_args):
        value = self._price_value()
        if value is not None:
            QgsSettings().setValue(SAWLOG_PRICE_SETTING_KEY, value)
        if hasattr(self, "run_button"):
            self._update_buttons()

    def _format_price(self):
        value = self._price_value()
        if value is not None:
            self.sawlog_price.setText(self.price_validator.locale().toString(value, "f", 2))

    def _hide_dock(self):
        parent = self.parentWidget()
        while parent is not None and parent.__class__.__name__ != "QDockWidget":
            parent = parent.parentWidget()
        if parent is not None:
            parent.hide()

    def _redock_dock(self):
        parent = self.parentWidget()
        while parent is not None and parent.__class__.__name__ != "QDockWidget":
            parent = parent.parentWidget()
        if parent is not None:
            parent.setFloating(False)
            self.iface.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, parent)
            parent.show()
            parent.raise_()

    def start_drawing(self):
        self.draw_mode.setChecked(True)
        canvas = self.iface.mapCanvas()
        self.draw_tool = PolygonDrawTool(canvas, self._set_drawn_aoi, self.language)
        canvas.setMapTool(self.draw_tool)
        self.aoi_status.setText(tr(self.language, "draw_instructions"))

    def _update_aoi_mode(self, *_args):
        use_layer = self.layer_mode.isChecked()
        use_drawn = self.draw_mode.isChecked()
        self.layer_controls.setEnabled(use_layer)
        self.draw_controls.setEnabled(use_drawn)
        if not use_drawn:
            canvas = self.iface.mapCanvas()
            if self.draw_tool is not None and canvas.mapTool() is self.draw_tool:
                if self.draw_tool.previous_tool is not None:
                    canvas.setMapTool(self.draw_tool.previous_tool)
                else:
                    canvas.unsetMapTool(self.draw_tool)
                self.draw_tool = None
        if use_layer:
            self._update_aoi_selection()
        elif use_drawn:
            self._update_drawn_aoi_status()
        else:
            self.aoi_status.setText(tr(self.language, "aoi_extent_status"))
        self._update_buttons()

    def _on_aoi_layer_changed(self, layer):
        if self._selection_layer is not None:
            try:
                self._selection_layer.selectionChanged.disconnect(self._on_aoi_selection_changed)
            except (TypeError, RuntimeError):
                pass
        if self._shutting_down:
            self._selection_layer = None
            return
        self._selection_layer = layer
        self._selection_choice_manually_set = False
        if self._selection_layer is not None:
            self._selection_layer.selectionChanged.connect(self._on_aoi_selection_changed)
        self._update_aoi_selection()
        if hasattr(self, "run_button"):
            self._refresh_layer_connections()

    def _on_aoi_selection_changed(self, *_args):
        self._update_aoi_selection()

    def _on_selected_only_toggled(self, checked):
        if self._updating_selection_choice:
            return
        self._selection_choice_manually_set = True
        self._update_aoi_selection()

    def _set_selected_only_checked(self, checked):
        if self.selected_only.isChecked() == checked:
            return
        self._updating_selection_choice = True
        try:
            self.selected_only.setChecked(checked)
        finally:
            self._updating_selection_choice = False

    def _update_aoi_selection(self):
        layer = self.layer_combo.currentLayer()
        selected_count = layer.selectedFeatureCount() if layer is not None else 0
        self.selected_only.setText(tr(
            self.language, "selected_only_count", count=selected_count
        ))
        self.selected_only.setEnabled(
            self.layer_mode.isChecked() and (selected_count > 0 or self.selected_only.isChecked())
        )
        if selected_count == 0 and not self._selection_choice_manually_set:
            self._set_selected_only_checked(False)
        elif not self._selection_choice_manually_set:
            self._set_selected_only_checked(True)
        self._update_buttons()
        if not self.layer_mode.isChecked():
            return
        if layer is None:
            self.aoi_status.setText(tr(self.language, "aoi_layer_status_none"))
        elif self.selected_only.isChecked():
            self.aoi_status.setText(tr(
                self.language,
                "aoi_layer_status_selected",
                name=layer.name(),
                count=selected_count,
            ))
        else:
            self.aoi_status.setText(tr(
                self.language, "aoi_layer_status_all", name=layer.name()
            ))

    def _update_drawn_aoi_status(self):
        if self.drawn_aoi is None:
            self.aoi_status.setText(tr(self.language, "drawn_aoi_none"))
            self.clear_drawn_aoi_button.setEnabled(False)
        else:
            self.aoi_status.setText(tr(self.language, "drawn_aoi_ready"))
            self.clear_drawn_aoi_button.setEnabled(True)
        if hasattr(self, "run_button"):
            self._refresh_layer_connections()

    def clear_drawn_aoi(self):
        canvas = self.iface.mapCanvas()
        if self.draw_tool is not None and canvas.mapTool() is self.draw_tool:
            if self.draw_tool.previous_tool is not None:
                canvas.setMapTool(self.draw_tool.previous_tool)
            else:
                canvas.unsetMapTool(self.draw_tool)
        self.draw_tool = None
        for layer in list(QgsProject.instance().mapLayers().values()):
            if layer.customProperty(RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "layer_id", "") == "drawn_analysis_area":
                QgsProject.instance().removeMapLayer(layer.id())
        self.drawn_aoi = None
        self._update_drawn_aoi_status()

    def _set_drawn_aoi(self, layer):
        if layer is None:
            self._update_drawn_aoi_status()
            return
        project = QgsProject.instance()
        for existing in list(project.mapLayers().values()):
            if existing.customProperty(RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "layer_id", "") == "drawn_analysis_area":
                project.removeMapLayer(existing.id())
        layer.setName(tr(self.language, "drawn_aoi_layer"))
        layer.setCustomProperty(RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "layer_id", "drawn_analysis_area")
        layer.setCustomProperty(RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "managed", True)
        symbol = QgsFillSymbol.createSimple({
            "color": "230,100,40,55",
            "outline_color": "230,100,40,255",
            "outline_width": "0.7",
        })
        layer.setRenderer(QgsSingleSymbolRenderer(symbol))
        project.addMapLayer(layer)
        self.iface.setActiveLayer(layer)
        self.drawn_aoi = layer
        self._update_drawn_aoi_status()

    def choose_output_folder(self):
        selected = QFileDialog.getExistingDirectory(self, tr(self.language, "output_folder"), self.output_folder.text())
        if selected:
            self.output_folder.setText(selected)
            self._remember_output_folder()

    def _remember_output_folder(self):
        folder = self.output_folder.text().strip()
        if folder:
            QgsSettings().setValue(OUTPUT_FOLDER_SETTING_KEY, folder)

    def _selected_aoi(self):
        if self.draw_mode.isChecked():
            return self.drawn_aoi
        if self.extent_mode.isChecked():
            canvas = self.iface.mapCanvas()
            extent = canvas.extent()
            crs = canvas.mapSettings().destinationCrs()
            layer = QgsVectorLayer(
                "Polygon?crs={0}".format(crs.authid()),
                tr(self.language, "extent_aoi_layer"),
                "memory",
            )
            feature = QgsFeature(layer.fields())
            feature.setGeometry(QgsGeometry.fromRect(extent))
            if not layer.dataProvider().addFeature(feature):
                raise RuntimeError(tr(self.language, "error_extent_aoi_create"))
            layer.updateExtents()
            return layer
        return self.layer_combo.currentLayer()

    def run_analysis(self):
        self._remember_output_folder()
        if self._analysis_task is not None:
            return
        if not self._inputs_ready():
            self.iface.messageBar().pushWarning(
                tr(self.language, "toolbar_name"), tr(self.language, "parameters_incomplete"))
            return
        aoi = self._selected_aoi()
        if aoi is None:
            self.iface.messageBar().pushWarning(
                tr(self.language, "toolbar_name"), tr(self.language, "aoi_missing")
            )
            return
        project = QgsProject.instance()
        sources = self._configured_sources()
        try:
            worker_inputs = capture_worker_inputs(
                aoi,
                sources,
                self.selected_only.isChecked() if self.layer_mode.isChecked() else False,
                project.transformContext(),
                self.language,
                self.output_folder.text().strip(),
                sawlog_price_eur_m3=self._price_value(),
            )
        except Exception as exc:
            self.iface.messageBar().pushCritical(
                tr(self.language, "toolbar_name"),
                tr(self.language, "run_error", error=str(exc)),
            )
            return

        task = ResponsibleForestPlanningAnalysisTask(
            tr(self.language, "progress_task_description"),
            worker_inputs,
            self._analysis_task_finished,
        )
        self._analysis_task = task
        self._analysis_cancel_requested = False
        self.cancel_button.setText(tr(self.language, "cancel_analysis"))
        self.cancel_button.setEnabled(True)
        self.run_button.setEnabled(False)
        QgsApplication.taskManager().addTask(task)

    def cancel_analysis(self):
        task = self._analysis_task
        if task is None or self._analysis_cancel_requested:
            return
        self._analysis_cancel_requested = True
        self.cancel_button.setText(tr(self.language, "canceling_analysis"))
        self.cancel_button.setEnabled(False)
        task.cancel()

    def shutdown(self):
        """Cancel owned analysis and detach callbacks before widgets are deleted."""
        self._shutting_down = True
        self._disconnect_layer_connections()
        self._disconnect_signals(self._external_connections)
        if self._selection_layer is not None:
            try:
                self._selection_layer.selectionChanged.disconnect(self._on_aoi_selection_changed)
            except (TypeError, RuntimeError):
                pass
            self._selection_layer = None
        task = self._analysis_task
        if task is not None:
            task.detach_completion_callback()
            task.cancel()
            self._clear_analysis_state()

    def _clear_analysis_state(self):
        self._analysis_task = None
        self._analysis_cancel_requested = False
        self.cancel_button.setText(tr(self.language, "cancel_analysis"))
        self.cancel_button.setEnabled(False)
        self._update_buttons()

    def _analysis_task_finished(self, task, successful):
        self._clear_analysis_state()
        if successful:
            gpkg_path = str(task.result.get("gpkg_path", ""))
            workbook_path = str(task.result.get("xlsx_path", ""))
            try:
                self._add_result_layer(gpkg_path)
                self.iface.messageBar().pushSuccess(
                    tr(self.language, "toolbar_name"),
                    tr(self.language, "run_complete", gpkg=gpkg_path, workbook=workbook_path),
                )
                for warning in task.result.get("warnings", []):
                    self.iface.messageBar().pushWarning(tr(self.language, "toolbar_name"), warning)
            except Exception as exc:
                self.iface.messageBar().pushCritical(
                    tr(self.language, "toolbar_name"), tr(self.language, "run_error", error=str(exc))
                )
        else:
            if task.cancellation_requested():
                self.iface.messageBar().pushWarning(
                    tr(self.language, "toolbar_name"), tr(self.language, "error_cancelled")
                )
                return
            self.iface.messageBar().pushCritical(
                tr(self.language, "toolbar_name"),
                tr(self.language, "run_error", error=str(task.error or tr(self.language, "error_task_failed"))),
            )

    def _add_result_layer(self, gpkg_path):
        project = QgsProject.instance()
        results = results_group(project, self.language)
        run_name = os.path.splitext(os.path.basename(gpkg_path))[0]
        result_uri = gpkg_path + "|layername=classified_forest_polygons"

        class_layers = []
        class_codes = (
            ("SENSITIVE", "class_sensitive"),
            ("ECONOMIC", "class_economic"),
            ("UNKNOWN", "class_unknown"),
        )
        for tier, _label in TIERS:
            for class_code, class_key in class_codes:
                subset = '"class_{0}" = \'{1}\''.format(tier, class_code)
                # Open with the filter already applied. Mutating a live OGR
                # source can disrupt other readers of this same GeoPackage.
                class_layer = QgsVectorLayer(
                    result_uri + "|subset=" + subset,
                    "{0} - {1}".format(
                        tr(self.language, "tier_" + tier),
                        tr(self.language, class_key),
                    ),
                    "ogr",
                )
                if not class_layer.isValid():
                    raise RuntimeError("GeoPackage class view could not be reopened.")
                if class_layer.subsetString() != subset:
                    raise RuntimeError("Could not apply the class filter to a result view.")
                class_layer.setRenderer(QgsSingleSymbolRenderer(self._class_symbol(class_code)))
                class_layer.setCustomProperty(RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "class_view", True)
                class_layers.append((tier, class_layer))

        # Publish clipped snapshots so the output shows the evidence actually classified,
        # rather than a later view of the original source layers.
        snapshot_layers = []
        snapshot_name_keys = (
            ("forest_centre_stand", "stand_layer"),
            ("forest_centre_habitat", "habitat_layer"),
            ("syke_protected_areas_state_owned", "protected_state_layer"),
            ("syke_protected_areas_private_land", "protected_private_layer"),
            ("syke_protected_areas_wilderness", "protected_wilderness_layer"),
            "syke_nature_conservation_programme_areas",
            ("syke_groundwater_areas", "groundwater_layer"),
            ("forest_centre_gridcell", "gridcell_layer"),
        )
        for item in snapshot_name_keys:
            service_id, name_key = item if isinstance(item, tuple) else (item, "programme_layer")
            uri = gpkg_path + "|layername=" + service_id
            snapshot = QgsVectorLayer(uri, tr(self.language, name_key), "ogr")
            if snapshot.isValid():
                snapshot_layers.append(snapshot)

        run_group = results.addGroup(run_name)
        run_group.setCustomProperty(RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX + "run_group", run_name)
        active_layer = None
        for tier, class_layer in class_layers:
            tier_group = run_group.findGroup(tr(self.language, "tier_" + tier))
            if tier_group is None:
                tier_group = run_group.addGroup(tr(self.language, "tier_" + tier))
            project.addMapLayer(class_layer, False)
            node = tier_group.addLayer(class_layer)
            visible = tier == "all_out"
            node.setItemVisibilityChecked(True)
            if visible and active_layer is None:
                active_layer = class_layer
        for tier, _label in TIERS:
            tier_group = run_group.findGroup(tr(self.language, "tier_" + tier))
            if tier_group is not None:
                tier_group.setItemVisibilityChecked(tier == "all_out")
        if snapshot_layers:
            inputs_group = run_group.addGroup(tr(self.language, "run_inputs_group"))
            for snapshot in snapshot_layers:
                snapshot.setName("{0} ({1})".format(snapshot.name(), tr(self.language, "run_input_suffix")))
                project.addMapLayer(snapshot, False)
                node = inputs_group.addLayer(snapshot)
                node.setItemVisibilityChecked(True)
            inputs_group.setItemVisibilityChecked(False)
        if active_layer is not None:
            self.iface.setActiveLayer(active_layer)

    def _class_symbol(self, class_code):
        color = {
            "SENSITIVE": "219,75,63,255",
            "ECONOMIC": "75,160,90,255",
            "UNKNOWN": "145,145,145,255",
        }[class_code]
        return QgsFillSymbol.createSimple({
            "color": color,
            "outline_color": "55,55,55,255",
            "outline_width": "0.15",
        })

    def capture_state(self):
        selected_layer = self.layer_combo.currentLayer()
        return {
            "layer": selected_layer,
            "selected_only": self.selected_only.isChecked(),
            "selection_choice_manually_set": self._selection_choice_manually_set,
            "aoi_mode": (
                "draw" if self.draw_mode.isChecked()
                else "extent" if self.extent_mode.isChecked()
                else "layer"
            ),
            "output_folder": self.output_folder.text(),
            "sawlog_price": self.sawlog_price.text(),
            "drawn_aoi": self.drawn_aoi,
        }

    def restore_state(self, state, page=0):
        if not state:
            return
        if state.get("layer") is not None:
            self.layer_combo.setLayer(state["layer"])
        self.output_folder.setText(state.get("output_folder", ""))
        self.sawlog_price.setText(state.get("sawlog_price", ""))
        self.drawn_aoi = state.get("drawn_aoi")
        if state.get("aoi_mode") == "draw":
            self.draw_mode.setChecked(True)
        elif state.get("aoi_mode") == "extent":
            self.extent_mode.setChecked(True)
        else:
            self.layer_mode.setChecked(True)
        self.selected_only.setChecked(bool(state.get("selected_only")))
        self._selection_choice_manually_set = bool(state.get("selection_choice_manually_set", False))
        self._update_aoi_mode()
        if self.drawn_aoi is not None:
            self.drawn_aoi.setName(tr(self.language, "drawn_aoi_layer"))
            self._update_drawn_aoi_status()
        self.pages.setCurrentIndex(min(max(0, page), self.pages.count() - 1))
