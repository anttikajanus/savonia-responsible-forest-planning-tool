# Separate technical diagnostics from business-action records

Status: accepted  
Recorded: 2026-10-26

Use Python module loggers under the plugin namespace for detailed rotating `technical.log` records and concise forwarding to QGIS's existing Log Messages panel. Record meaningful operation outcomes separately in `business-actions.jsonl`, with minimal aggregate attributes; this avoids mixing usage records with tracebacks or building a second log viewer. Both files stay in the QGIS per-user settings area with 2 MiB rotation and three backups, while unload closes only plugin-owned handlers. These are local operational records; durable analysis provenance belongs in the outputs. See [operations](../operations.md#logging) and [logging implementation](../../../qgis_plugin/savonia_responsible_forest_planning_tool/app_logging.py).
