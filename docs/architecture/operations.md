# Operational design

The [development guide](development.md) owns setup, debugging, test and packaging
procedures. [QGIS guidance](../agents/qgis.md) owns the implementation and
localization workflow. This page explains the runtime policies behind them.

## Logging

Technical diagnostics and aggregate business-action records have separate local
channels. Technical logs retain tracebacks and relevant run/stage/source context;
selected concise messages also reach QGIS Log Messages. Business-action records
retain stable events, outcomes, run IDs, entry points and necessary aggregate
counts/choices. They exclude user identity, paths, project/layer names,
credentials and feature-level data. Credentials and unnecessary personal/source
data stay out of both channels. These are operational records, not telemetry;
durable analysis provenance belongs in exported run metadata.
[ADR-0007](adr/0007-separate-operational-log-channels.md).

Files live under the QGIS per-user settings directory at
`savonia_responsible_forest_planning_tool/logs/`: `technical.log` and
`business-actions.jsonl`. Each rotates at 2 MiB with three backups and uses UTC
timestamps. The [logging module](../../qgis_plugin/savonia_responsible_forest_planning_tool/app_logging.py)
owns handler configuration and forwarding mechanics. Initialization/reload and
unload manage only plugin-owned handlers, preserving QGIS's process-wide logger.
Log failures must preserve the original analysis error and keep the application
usable, with a panel warning when possible.

Processing feedback carries progress, cancellation and recoverable messages;
short translated UI summaries provide corrective actions. Repeated feature
problems are aggregated with bounded ID samples. Stand-overlap pair evidence
belongs in technical logs, with an aggregate completion warning; metric missing
values are explained by durable coverage rather than a per-value log stream.

## Development and verification

Use [development](development.md) for runtime setup and repeatable checks.
Remaining provider/desktop questions belong in
[open questions](../open-questions.md). Automated checks and adopted policies do
not establish interactive or live-provider acceptance.

## Language and help

QGIS is the sole language setting: Finnish QGIS uses Finnish; all other or
unavailable languages use English. Each run carries one resolved presentation
language through progress, errors and outputs. Stable field/source IDs,
configuration keys, event/status values and machine timestamps remain
language-neutral. The [translation catalogue](../../qgis_plugin/savonia_responsible_forest_planning_tool/i18n.py)
provides equivalent Finnish/English text and named placeholders.
[ADR-0008](adr/0008-qgis-language-and-offline-help.md).

Canonical [Finnish](../help/manual_fi.html) and [English](../help/manual_en.html)
HTML manuals live under `docs/help/`; packaging includes both alongside original
legal texts and keeps resource links local. The shared
[help resolver](../../qgis_plugin/savonia_responsible_forest_planning_tool/documentation.py)
selects the same language as the plugin, including Processing help, and reports
missing resources or launch failures with translated corrective messages. This
avoids divergent fallback choices between QGIS help and the plugin. Offline
help does not imply offline analysis sources.

Help/About are available with the dock closed. QGIS language refresh updates
plugin-owned labels and subsequent help launches; both manuals maintain matching
anchors, and original legal notices stay untranslated. Observable requirements
and desktop checks belong to [help and language](../specs/help-and-language.md)
and the [verification register](../open-questions.md#interactive-acceptance).
