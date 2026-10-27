"""Savonia - Responsible Forest Planning QGIS plugin."""


def classFactory(iface):
    from .ui.plugin import ResponsibleForestPlanningPlugin

    return ResponsibleForestPlanningPlugin(iface)
