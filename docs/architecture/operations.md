# Development and operations

The [development guide](development.md) owns setup, reload, debugger, test and packaging commands. [Agent QGIS guidance](../agents/qgis.md) owns the required implementation/testing/localization workflow. This page describes the operational design and its rationale.

## Logging

Logging constants retain descriptive module-local names in `app_logging.py`,
including `LOGGER_NAME`, `BUSINESS_LOGGER_NAME`, `PLUGIN_TAG` and
`LOG_DIRECTORY_NAME`. Their existing logger names, display tag, directory and
rotation values remain stable; identifier cleanup does not change destinations.

The plugin uses module loggers under `savonia_responsible_forest_planning_tool`, configured once at plugin initialization, with propagation disabled. The plugin does not configure the process-wide root logger. Technical diagnostics go to UTF-8 `technical.log` at DEBUG and selected INFO/WARNING/ERROR records go one-way to QGIS's Log Messages panel under the stable plugin tag. ERROR/CRITICAL maps to QGIS Critical, WARNING to Warning, other selected records to Info; routine messages use `notifyUser=False` and panel forwarding strips tracebacks. The detailed file retains them. [ADR-0007](adr/0007-separate-operational-log-channels.md), [app_logging.py](../../qgis_plugin/savonia_responsible_forest_planning_tool/app_logging.py).

Structured operation events use a separate logger and UTF-8 `business-actions.jsonl`: timestamp, stable event, outcome/context, run ID, entry point and necessary aggregate counts/choices. These are local operational records, not telemetry or the durable analysis record. Avoid user identity, project/layer names, paths, credentials and feature-level data in this channel. Technical diagnostics may retain the minimum relevant source/stage identifiers needed to reproduce a defect; credentials and unnecessary source/personal data stay out of both channels.

Both files live at `QgsApplication.qgisSettingsDirPath()/savonia_responsible_forest_planning_tool/logs/`. Each rotates at 2 MiB with three backups; timestamps are UTC. A file-open failure keeps the application usable and emits a diagnostic-panel warning when possible. Configure/reload removes prior owned handlers; unload detaches and closes only the plugin's handlers. Python's [logging handler model](https://docs.python.org/3/library/logging.html), [library logging guidance](https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library), [rotation support](https://docs.python.org/3/library/logging.handlers.html#rotatingfilehandler), and [QGIS communication guidance](https://docs.qgis.org/4.2/en/docs/pyqgis_developer_cookbook/communicating.html) support this design.

Use the QGIS panel for support diagnostics, Processing feedback for progress/cancellation and recoverable messages, and short UI summaries for corrective action. Preserve a traceback and run/stage context for unexpected failures. Aggregate repeated feature problems and cap ID samples. Provenance needed for reproducibility belongs in run metadata rather than depending on rotated logs.

The [logging contract tests](../../qgis_plugin/tests/qgis/test_logging_contract.py)
verify handler ownership, rotation configuration, correlated aggregate events,
traceback separation and log-directory/file-open failures in a temporary profile.
They do not establish behavior for every possible filesystem failure.

## Development and verification

Use [development](development.md) for profile/reload setup, runtime policy,
test commands and package verification. The
[QGIS guidance](../agents/qgis.md#testing-and-debugging) defines the required
implementation workflow. Current evidence gaps and acceptance status belong in
[open questions](open-questions.md), not in these repeatable procedures.

## Language and help

`selected_language()` resolves `QgsApplication.locale()`: Finnish QGIS uses Finnish and all other/unavailable languages use English. It imports QGIS inside that guarded detection path; translation catalogue lookups and explicit-language workbook exports work with ordinary Python. QGIS is the sole language setting; the wizard has no independent language selector. Stable identifiers, field IDs, configuration keys, status/event values and machine timestamps remain language-neutral. Translate presentation and errors using the existing `i18n.py` catalogue with named placeholders, equivalent keys and locale-appropriate presentation. [ADR-0008](adr/0008-qgis-language-and-offline-help.md), [current language implementation](../../qgis_plugin/savonia_responsible_forest_planning_tool/i18n.py).

Maintain equivalent [Finnish](../help/manual_fi.html) and [English](../help/manual_en.html) HTML manuals under `docs/help/`; source-linked development resolves them there. Packaging bundles them under the installed plugin's `docs/help/` and adjusts legal-resource links to stay inside the package. Ship full original legal texts inside the plugin package. Help/About work under QGIS Help → Plugins even with the dock closed, and from the dock in either mode. Processing provides translated `shortHelpString()` and a `helpUrl()` to the same selected manual's Processing anchor. The shared resolver builds encoded local file URLs, validates requested resources/anchors and reports missing files or browser-launch failures with translated corrective messages. External websites supplement the local manual; offline documentation does not imply offline analysis sources. [Resource resolver](../../qgis_plugin/savonia_responsible_forest_planning_tool/documentation.py), [QGIS 4.2 pluginHelpMenu API](https://api.qgis.org/api/4.2/classQgisInterface.html), [Processing help API](https://api.qgis.org/api/4.2/classQgsProcessingAlgorithm.html).

QGIS's built-in `showPluginHelp()` uses its own locale/fallback sequence. Explicitly selecting the same language as the rest of this plugin avoids divergent help choices; package URLs must also work from paths with spaces/non-ASCII characters. Keep matching anchors in both manuals and original legal notices untranslated. About reads the installed version from metadata and exposes notices, inventory, sources and links to online documentation, the GitHub repository and GitHub Issues. [QGIS 4.2.3 help implementation](https://github.com/qgis/QGIS/blob/final-4_2_3/python/utils.py), [help requirements](../specs/help-and-language.md).

When QGIS language is refreshed, refresh plugin-owned labels and any open About dialog; subsequent manual launches use the new language. An external browser page need not refresh itself. Check both languages, unsupported-language fallback, failures, offline resources and cleanup after reload. The translation mechanism is the `i18n.py` catalogue. General translation principles come from [Qt internationalization](https://doc.qt.io/qt-6/i18n-source-translation.html), with exact APIs checked against QGIS's bundled runtime.

Interactive desktop/browser/network-disconnected checks remain listed in [open questions](open-questions.md#acceptance-and-distribution). Existing verification records must retain the difference between automated coverage and manual acceptance.
