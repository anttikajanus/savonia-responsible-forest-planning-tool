"""Public Help/About follow QGIS's language in the supported Qt/QGIS runtime."""

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.environ.get(
    "RESPONSIBLE_FOREST_PLANNING_TEST_PLUGIN_ROOT",
    os.environ.get("SAVONIA_TEST_PLUGIN_ROOT", str(Path(__file__).resolve().parents[2])),
))

from qgis.core import QgsApplication, QgsFeature, QgsGeometry, QgsProject, QgsVectorLayer
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt.QtWidgets import QComboBox, QLabel

APP = QgsApplication.instance()
if APP is None:
    APP = QgsApplication([], True)
    APP.initQgis()

from savonia_responsible_forest_planning_tool.i18n import selected_language, tr
from savonia_responsible_forest_planning_tool.ui.plugin import ResponsibleForestPlanningPlugin


from ui_fixture import Interface


class HelpUiTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name) / "Asennettu lisäosa"
        self.root.mkdir()
        (self.root / "docs" / "help").mkdir(parents=True)
        for language in ("fi", "en"):
            (self.root / "docs" / "help" / f"manual_{language}.html").write_text(
                '<html><body><h1 id="workflow">Workflow</h1>'
                '<h2 id="data-sources">Sources</h2></body></html>', encoding="utf-8")
        (self.root / "metadata.txt").write_text(
            "[general]\nname=Savonia - Responsible Forest Planning\nversion=9.8.7\n"
            "name[fi]=Savonia - Vastuullinen metsäsuunnittelu\n"
            "homepage=https://github.com/anttikajanus/savonia-responsible-forest-planning-tool/tree/main/docs/help\n"
            "repository=https://github.com/anttikajanus/savonia-responsible-forest-planning-tool\n"
            "tracker=https://github.com/anttikajanus/savonia-responsible-forest-planning-tool/issues\n", encoding="utf-8")
        self.qgis_locale = self.enterContext(patch.object(QgsApplication, "locale", return_value="fi_FI"))
        self.enterContext(patch.object(QgsApplication, "qgisSettingsDirPath", return_value=self.folder.name))
        self.launch = self.enterContext(patch.object(QDesktopServices, "openUrl", return_value=True))
        self.iface = Interface()
        self.addCleanup(self.iface.window.deleteLater)
        self.plugin = ResponsibleForestPlanningPlugin(self.iface, package_root=self.root)
        self.addCleanup(self.plugin.unload)
        self.plugin.initGui()

    def test_setup_is_first_in_wizard_toolbar_and_localized_in_both_dock_modes(self):
        self.iface.window.resize(1000, 800)
        self.iface.window.show()
        wizard = self.plugin.wizard
        before_layers = set(QgsProject.instance().mapLayers())
        self.assertEqual(self.plugin.toolbar.actions(), [self.plugin.wizard_action])
        self.assertIn(self.plugin.setup_action, self.iface.plugin_menu.actions())
        actions = wizard.toolbar.actions()
        self.assertEqual(actions[0], wizard.setup_action)
        self.assertTrue(actions[1].isSeparator())
        self.assertEqual(actions[2:], [wizard.redock_action, wizard.help_action, wizard.about_action])
        for language in ("en", "fi"):
            self.qgis_locale.return_value = language
            self.plugin.show_wizard()
            for floating in (False, True):
                with self.subTest(language=language, floating=floating):
                    self.plugin.dock.setFloating(floating)
                    APP.processEvents()
                    self.assertEqual(wizard.toolbar.iconSize(), self.iface.iconSize(True))
                    button = wizard.toolbar.widgetForAction(wizard.setup_action)
                    self.assertTrue(button.isVisible())
                    self.assertTrue(wizard.setup_action.isEnabled())
                    self.assertFalse(wizard.setup_action.icon().isNull())
                    self.assertEqual(button.accessibleName(), tr(language, "setup_project"))
                    for action in (wizard.setup_action, self.plugin.setup_action):
                        self.assertEqual(action.text(), tr(language, "setup_project"))
                        self.assertEqual(action.toolTip(), tr(language, "tooltip_setup_project"))
                        self.assertEqual(action.statusTip(), tr(language, "tooltip_setup_project"))
        self.assertEqual(set(QgsProject.instance().mapLayers()), before_layers)

    def test_setup_shortcuts_call_shared_handler_once_after_each_reload(self):
        self.plugin.unload()
        with patch.object(self.plugin, "setup_project_layers") as setup:
            for _ in range(2):
                self.plugin.initGui()
                self.plugin.initGui()
                self.assertFalse(self.plugin.dock.isVisible())
                self.assertEqual(self.iface.plugin_menu.actions(),
                                 [self.plugin.wizard_action, self.plugin.setup_action])
                self.assertEqual(self.plugin.toolbar.actions(), [self.plugin.wizard_action])
                self.plugin.setup_action.trigger()
                setup.assert_called_once()
                setup.reset_mock()
                self.plugin.show_wizard()
                self.plugin.wizard.setup_action.trigger()
                setup.assert_called_once()
                setup.reset_mock()
                self.plugin.unload()
                APP.processEvents()
                self.assertEqual(self.iface.plugin_menu.actions(), [])

    def test_wizard_is_localized_and_keeps_prototype_notice_in_about(self):
        self.iface.window.resize(1100, 850)
        self.iface.window.show()
        for language, title in (("en", "Savonia - Responsible Forest Planning"),
                                ("fi", "Savonia - Vastuullinen metsäsuunnittelu"),
                                ("en", "Savonia - Responsible Forest Planning")):
            with self.subTest(language=language):
                self.qgis_locale.return_value = language
                self.plugin.show_wizard()
                self.plugin.show_about()
                APP.processEvents()
                wizard = self.plugin.wizard
                self.assertEqual(self.plugin.dock.windowTitle(), title)
                self.assertTrue(self.plugin.about_dialog.content.toPlainText().startswith(title))
                for label in wizard.findChildren(QLabel):
                    self.assertNotIn(tr(language, "prototype_notice"), label.text())
                for widget, key in (
                    (wizard.heading, "wizard_heading"),
                    (wizard.description, "wizard_description"),
                    (wizard.layer_mode, "aoi_mode_layer"),
                    (wizard.draw_mode, "aoi_mode_draw"),
                    (wizard.extent_mode, "aoi_mode_extent"),
                    (wizard.draw_button, "draw_aoi"),
                    (wizard.clear_drawn_aoi_button, "clear_drawn_aoi"),
                    (wizard.output_folder_label, "output_folder"),
                    (wizard.run_button, "run"),
                    (wizard.cancel_button, "cancel_analysis"),
                    (wizard.close_button, "close"),
                ):
                    self.assertEqual(widget.text(), tr(language, key))
                    self.assertEqual(widget.accessibleName(), tr(language, key))
                self.assertEqual(wizard.area_group.title(), tr(language, "analysis_area_group"))
                for key in ("toolbar_name", "wizard_title", "algorithm_name",
                            "help_menu", "about_menu"):
                    self.assertNotIn("protot", tr(language, key).lower())
                self.assertIn(tr(language, "prototype_notice"), self.plugin.about_dialog.content.toPlainText())
                self.assertEqual(self.plugin.processing_provider.name(), tr(language, "toolbar_name"))

    def test_help_works_with_dock_closed_and_unload_removes_actions(self):
        self.plugin.initGui()
        self.assertFalse(self.plugin.dock.isVisible())
        self.assertEqual([action.text() for action in self.iface.help_menu.actions()],
                         [tr("fi", "help_menu"), tr("fi", "about_menu")])
        before_layers = set(QgsProject.instance().mapLayers())
        self.iface.help_menu.actions()[0].trigger()
        url = self.launch.call_args.args[0]
        self.assertTrue(url.isLocalFile())
        self.assertTrue(url.toLocalFile().endswith("manual_fi.html"))
        self.assertEqual(url.fragment(), "workflow")
        self.assertEqual(set(QgsProject.instance().mapLayers()), before_layers)
        self.plugin.unload()
        self.assertEqual(self.iface.help_menu.actions(), [])
        self.plugin.initGui()
        self.assertEqual(len(self.iface.help_menu.actions()), 2)

    def test_about_uses_installed_metadata_and_shows_complete_offline_legal_text(self):
        licence = "MIT License\nCopyright (c) 2026 Antti Kajanus\nPermission is hereby granted.\n"
        (self.root / "LICENSE").write_text(licence, encoding="utf-8")
        self.plugin.show_about()
        dialog = self.plugin.about_dialog
        self.assertTrue(dialog.isVisible())
        content = dialog.content.toPlainText()
        for text in ("9.8.7", "Savonia", "Antti Kajanus", "Lähdekoodivarasto", "Aineistolähteet"):
            self.assertIn(text, content)
        dialog.content.anchorClicked.emit(QUrl("savonia:licence"))
        self.assertEqual(dialog.legal_text.toPlainText(), licence)
        self.assertEqual(self.launch.call_count, 0)
        for language in ("fi", "en"):
            dialog.set_language(language)
            dialog.content.anchorClicked.emit(QUrl("savonia:homepage"))
            self.assertEqual(
                self.launch.call_args.args[0].toString(),
                "https://github.com/anttikajanus/savonia-responsible-forest-planning-tool/tree/main/docs/help",
            )
        self.plugin.unload()
        self.assertFalse(dialog.isVisible())

    def test_qgis_language_refreshes_about_and_closed_dock_help_without_a_selector(self):
        self.plugin.show_wizard()
        self.plugin.show_about()
        wizard = self.plugin.wizard
        wizard.output_folder.setText("Chosen output")
        wizard.extent_mode.setChecked(True)
        self.assertEqual(wizard.toolbar.findChildren(QComboBox), [])
        self.qgis_locale.return_value = "en_GB"
        self.plugin.show_wizard()
        self.assertEqual(selected_language(), "en")
        self.assertEqual(wizard.output_folder.text(), "Chosen output")
        self.assertTrue(wizard.extent_mode.isChecked())
        self.assertEqual(self.plugin.about_dialog.windowTitle(), "About Savonia - Responsible Forest Planning (Prototype)")
        self.assertIn("Source repository", self.plugin.about_dialog.content.toPlainText())
        self.assertEqual(self.iface.help_menu.actions()[0].text(), tr("en", "help_menu"))
        self.assertEqual(wizard.help_action.toolTip(), "Open the offline user manual.")
        self.assertEqual(wizard.toolbar.widgetForAction(wizard.help_action).accessibleName(), "Help")
        self.plugin.dock.setFloating(True)
        wizard.help_action.trigger()
        self.assertTrue(self.launch.call_args.args[0].toLocalFile().endswith("manual_en.html"))
        self.plugin.dock.hide()
        self.qgis_locale.return_value = "fi_FI"
        self.iface.help_menu.actions()[0].trigger()
        self.assertTrue(self.launch.call_args.args[0].toLocalFile().endswith("manual_fi.html"))
        self.plugin.unload()
        self.plugin.initGui()
        self.assertEqual(self.iface.help_menu.actions()[0].text(), tr("fi", "help_menu"))

    def test_missing_manual_never_falls_back_and_reports_localized_recovery(self):
        for language, recovery in (("fi", "Asenna lisäosa uudelleen"), ("en", "Reinstall the plugin")):
            with self.subTest(language=language):
                self.qgis_locale.return_value = language
                (self.root / "docs" / "help" / f"manual_{language}.html").unlink()
                self.launch.reset_mock()
                with self.assertLogs("savonia_responsible_forest_planning_tool", level="WARNING") as logs:
                    self.plugin.show_help()
                self.assertFalse(self.launch.called)
                self.assertIn(recovery, self.iface.messages[-1][1])
                self.assertIn(f"manual_{language}.html", " ".join(logs.output))
                self.assertIn("unreadable", " ".join(logs.output))

    def test_language_roundtrip_preserves_layer_and_manual_selection_choice(self):
        layer = QgsVectorLayer("Polygon?crs=EPSG:3067", "AOI fixture", "memory")
        feature = QgsFeature()
        feature.setGeometry(QgsGeometry.fromWkt("POLYGON ((0 0, 10 0, 10 10, 0 10, 0 0))"))
        layer.dataProvider().addFeatures([feature])
        QgsProject.instance().addMapLayer(layer)
        self.addCleanup(QgsProject.instance().removeMapLayer, layer.id())
        layer.selectAll()
        wizard = self.plugin.wizard
        wizard.layer_combo.setLayer(layer)
        wizard.selected_only.setChecked(False)
        for language, status, heading in (
            ("en", "Using all features from “AOI fixture”.", "Prepare forest scenario inputs"),
            ("fi", "Käytetään kaikkia tason “AOI fixture” kohteita.", "Valmistele metsäskenaarioiden lähtötiedot"),
        ):
            with self.subTest(language=language):
                self.qgis_locale.return_value = language
                self.plugin.show_wizard()
                self.assertEqual(wizard.layer_combo.currentLayer(), layer)
                self.assertFalse(wizard.selected_only.isChecked())
                self.assertEqual(wizard.aoi_status.text(), status)
                self.assertEqual(wizard.heading.text(), heading)

    def test_language_roundtrip_refreshes_disabled_selection_count_in_draw_and_extent_modes(self):
        layer = QgsVectorLayer("Polygon?crs=EPSG:3067", "AOI fixture", "memory")
        feature = QgsFeature()
        feature.setGeometry(QgsGeometry.fromWkt("POLYGON ((0 0, 10 0, 10 10, 0 10, 0 0))"))
        layer.dataProvider().addFeatures([feature])
        QgsProject.instance().addMapLayer(layer)
        self.addCleanup(QgsProject.instance().removeMapLayer, layer.id())
        layer.selectAll()
        wizard = self.plugin.wizard
        wizard.layer_combo.setLayer(layer)
        wizard.selected_only.setChecked(False)
        for mode in (wizard.draw_mode, wizard.extent_mode):
            mode.setChecked(True)
            for language, label in (
                ("en", "Use selected features only (1 selected)"),
                ("fi", "Käytä vain valittuja kohteita (1 valittu)"),
            ):
                with self.subTest(mode=mode.text(), language=language):
                    self.qgis_locale.return_value = language
                    self.plugin.show_wizard()
                    self.assertEqual(wizard.selected_only.text(), label)
                    self.assertFalse(wizard.selected_only.isEnabled())
                    self.assertFalse(wizard.selected_only.isChecked())
                    self.assertTrue(mode.isChecked())
                    self.assertEqual(layer.selectedFeatureCount(), 1)
                    self.assertEqual(wizard.layer_combo.currentLayer(), layer)

    def test_language_roundtrip_renames_existing_drawn_area_without_changing_geometry_or_drawing(self):
        drawn = QgsVectorLayer("Polygon?crs=EPSG:3067", "Piirretty analyysialue", "memory")
        drawn.setCustomProperty("savonia/layer_id", "drawn_analysis_area")
        feature = QgsFeature()
        feature.setGeometry(QgsGeometry.fromWkt("POLYGON ((0 0, 10 0, 10 10, 0 10, 0 0))"))
        drawn.dataProvider().addFeatures([feature])
        QgsProject.instance().addMapLayer(drawn)
        self.addCleanup(QgsProject.instance().removeMapLayer, drawn.id())
        wizard = self.plugin.wizard
        state = {**wizard.capture_state(), "drawn_aoi": drawn, "aoi_mode": "draw"}
        wizard.restore_state(state)
        original_geometry = bytes(next(drawn.getFeatures()).geometry().asWkb())
        wizard.start_drawing()
        active_tool = self.iface.mapCanvas().mapTool()
        for mode in (wizard.draw_mode, wizard.extent_mode):
            mode.setChecked(True)
            original_state = wizard.capture_state()
            for language, name in (("en", "Drawn analysis area"), ("fi", "Piirretty analyysialue")):
                with self.subTest(mode=mode.text(), language=language):
                    self.qgis_locale.return_value = language
                    self.plugin.show_wizard()
                    self.assertEqual(drawn.name(), name)
                    self.assertEqual(bytes(next(drawn.getFeatures()).geometry().asWkb()), original_geometry)
                    self.assertEqual(wizard.capture_state(), original_state)
                    if mode is wizard.draw_mode:
                        self.assertIs(self.iface.mapCanvas().mapTool(), active_tool)

    def test_failed_browser_launch_does_not_prevent_offline_about_notices(self):
        (self.root / "THIRD_PARTY_NOTICES").write_text("Original notice\nFull legal terms.\n", encoding="utf-8")
        self.launch.return_value = False
        for language, recovery in (("fi", "Tarkista oletusselain"), ("en", "Check your default browser")):
            with self.subTest(language=language):
                self.qgis_locale.return_value = language
                with self.assertLogs("savonia_responsible_forest_planning_tool", level="WARNING"):
                    self.plugin.show_help()
                self.assertIn(recovery, self.iface.messages[-1][1])
                self.plugin.show_about()
                self.plugin.about_dialog.open_link(QUrl("savonia:notices"))
                self.assertEqual(self.plugin.about_dialog.legal_text.toPlainText(), "Original notice\nFull legal terms.\n")

    def test_missing_notice_and_metadata_report_recovery_without_opening_browser(self):
        self.plugin.show_about()
        with self.assertLogs("savonia_responsible_forest_planning_tool", level="WARNING"):
            self.plugin.about_dialog.open_link(QUrl("savonia:licence"))
        self.assertIn("Asenna lisäosa uudelleen", self.iface.messages[-1][1])
        self.assertFalse(self.launch.called)
        self.plugin.unload()
        self.plugin.initGui()
        (self.root / "metadata.txt").unlink()
        with self.assertLogs("savonia_responsible_forest_planning_tool", level="WARNING"):
            self.plugin.show_about()
        self.assertIsNone(self.plugin.about_dialog)
        self.assertIn("Asenna lisäosa uudelleen", self.iface.messages[-1][1])


if __name__ == "__main__":
    unittest.main()
