# Share one application workflow between wizard and Processing

Status: accepted  
Recorded: 2026-10-26

Wizard-only analysis would duplicate rules when toolbox, batch or modeler use is added. Both entry points therefore call the same `run_workflow(parameters, feedback)`, with pure interpretation/calculation policy, QGIS geometry and provider adapters, cohesive execution phases, and separate file writers. This makes rule changes testable without widgets and keeps both entry points consistent, at the cost of explicit parameter/result and worker ownership boundaries. See the [architecture overview](../overview.md), [workflow source](../../../qgis_plugin/savonia_responsible_forest_planning_tool/analysis/workflow.py), and [QGIS Processing integration](https://docs.qgis.org/4.2/en/docs/pyqgis_developer_cookbook/processing.html).
