"""Savonia - Responsible Forest Planning QGIS plugin."""


def classFactory(iface):
    from .ui.plugin import SavoniaForestPlanningPlugin

    return SavoniaForestPlanningPlugin(iface)
