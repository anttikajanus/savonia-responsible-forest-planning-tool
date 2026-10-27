"""Small QGIS interface adapter with real Qt widgets for offscreen acceptance."""

from qgis.gui import QgsMapCanvas
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtWidgets import QMainWindow, QMenu

class Interface:
    """Real Qt controls behind the small QGIS interface boundary used here."""

    def __init__(self):
        self.window = QMainWindow()
        self.canvas = QgsMapCanvas(self.window)
        self.help_menu = QMenu(self.window)
        self.plugin_menu = QMenu(self.window)
        self.messages = []
        self.message_levels = []
        self.active_layer = None

    def mainWindow(self):
        return self.window

    def iconSize(self, dockedToolbar=False):
        size = 16 if dockedToolbar else 24
        return QSize(size, size)

    def mapCanvas(self):
        return self.canvas

    def addToolBar(self, title):
        return self.window.addToolBar(title)

    def pluginHelpMenu(self):
        return self.help_menu

    def addPluginToMenu(self, title, action):
        self.plugin_menu.addAction(action)

    def removePluginMenu(self, title, action):
        self.plugin_menu.removeAction(action)

    def addDockWidget(self, area, dock):
        self.window.addDockWidget(area, dock)

    def removeDockWidget(self, dock):
        self.window.removeDockWidget(dock)

    def messageBar(self):
        return self

    def pushWarning(self, title, message):
        self.messages.append((title, message))
        self.message_levels.append("warning")

    def pushSuccess(self, title, message):
        self.messages.append((title, message))
        self.message_levels.append("success")

    def pushCritical(self, title, message):
        self.messages.append((title, message))
        self.message_levels.append("critical")

    def setActiveLayer(self, layer):
        self.active_layer = layer

