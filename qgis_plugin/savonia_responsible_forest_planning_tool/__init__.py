"""Savonia - Responsible Forest Planning QGIS plugin."""

# Namespace for the plugin's QGIS custom properties.
RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX = "savonia/"


def classFactory(iface):
    from .ui.plugin import ResponsibleForestPlanningPlugin

    return ResponsibleForestPlanningPlugin(iface)
