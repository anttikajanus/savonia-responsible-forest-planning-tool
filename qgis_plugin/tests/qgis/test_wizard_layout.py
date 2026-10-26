"""Keep the wizard form compact when the dock gains vertical space."""

import os
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.environ.get(
    "SAVONIA_TEST_PLUGIN_ROOT", str(Path(__file__).resolve().parents[2])
))

from qgis.PyQt.QtCore import QPoint, QSize
from qgis.PyQt.QtWidgets import QLabel
from qgis.core import QgsApplication

APP = QgsApplication.instance()
if APP is None:
    APP = QgsApplication([], False)
    APP.initQgis()

from savonia_responsible_forest_planning_tool.ui.wizard import ForestPlanningWizard


class WizardLayoutTest(unittest.TestCase):
    def test_toolbar_uses_qgis_dock_icon_size(self):
        for language in ("fi", "en"):
            for pixels in (16, 24, 32):
                with self.subTest(language=language, pixels=pixels):
                    size = QSize(pixels, pixels)
                    iface = Mock()
                    iface.iconSize.return_value = size
                    wizard = ForestPlanningWizard(iface, language)
                    try:
                        self.assertEqual(wizard.toolbar.iconSize(), size)
                        iface.iconSize.assert_called_once_with(True)
                        for action in (wizard.setup_action, wizard.redock_action,
                                       wizard.help_action, wizard.about_action):
                            self.assertEqual(
                                wizard.toolbar.widgetForAction(action).iconSize(), size,
                            )
                    finally:
                        wizard.close()
                        wizard.deleteLater()
                        APP.processEvents()

    def test_extra_dock_height_stays_below_the_form(self):
        for language in ("fi", "en"):
            for width in (480, 860):
                with self.subTest(language=language, width=width):
                    iface = Mock()
                    iface.iconSize.return_value = QSize(16, 16)
                    wizard = ForestPlanningWizard(iface, language)
                    try:
                        wizard.resize(width, 650)
                        wizard.show()
                        APP.processEvents()
                        page = wizard.pages.currentWidget()
                        controls = [
                            wizard.toolbar,
                            *page.findChildren(QLabel),
                            wizard.layer_mode, wizard.layer_combo,
                            wizard.selected_only, wizard.draw_mode,
                            wizard.draw_button, wizard.extent_mode,
                            wizard.output_folder,
                        ]

                        def geometry(control):
                            return (
                                control.mapTo(wizard, QPoint()).y(),
                                control.height(),
                            )

                        compact = [geometry(control) for control in controls]
                        for height in (1000, 1400):
                            wizard.resize(width, height)
                            APP.processEvents()
                            self.assertEqual(
                                [geometry(control) for control in controls],
                                compact,
                                "Extra height must not spread out the form controls",
                            )
                            self.assertLessEqual(
                                wizard.height() - wizard.run_button.geometry().bottom(),
                                wizard.layout().contentsMargins().bottom() + 1,
                                "The action row must stay at the bottom of the dock",
                            )
                    finally:
                        wizard.close()
                        wizard.deleteLater()
                        APP.processEvents()


if __name__ == "__main__":
    unittest.main()
