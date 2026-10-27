"""Savonia - Responsible Forest Planning QGIS plugin."""

# Stored values remain stable for existing projects, settings and models.
RESPONSIBLE_FOREST_PLANNING_PROPERTY_PREFIX = "savonia/"


def classFactory(iface):
    from .ui.plugin import ResponsibleForestPlanningPlugin

    return ResponsibleForestPlanningPlugin(iface)
