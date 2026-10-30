# QGIS plugin implementation guidance

Read this guide before reading, changing, reviewing, testing, packaging or
documenting code under `qgis_plugin/`. It owns the plugin implementation,
verification and Finnish/English localization workflow. The
[documentation map](README.md) identifies the other owners.

Keep `metadata.txt` authoritative for the installation range. Use QGIS 4.2.3 as
the verification baseline and repeat the suites and packaged lifecycle/Processing
checks on newer targeted releases before recording them as verified.

## Read the affected contract

| Work | Read before changing it |
| --- | --- |
| Shared workflow, module or worker boundaries | [Architecture overview](../architecture/overview.md) and relevant [ADRs](../architecture/README.md#architecture-decision-records) |
| Observable behavior or acceptance | Affected [functional specifications](../specs/README.md) and [specification handoff](specifications.md) |
| Provider access, readiness or source fields | [Data sources](../architecture/data-sources.md), [source-layer requirements](../architecture/source-layer-requirements.md), then [local references](../references/service-metadata/README.md) |
| Geometry, classification or aggregation | [Calculation contracts](../architecture/calculations.md) and [indicator limitations](../architecture/indicators.md) |
| Logging, help, language or distribution | [Operations](../architecture/operations.md), [help/language requirements](../specs/help-and-language.md) and affected [distribution rules](../architecture/distribution.md) |
| Setup, tests or packaging commands | [Development guide](../architecture/development.md); it owns the executable commands |

## Required implementation workflow

For each feature or bug fix:

1. **Define behavior and failure policy.** State inputs, outputs, CRS and units, missing-data behavior, valid geometry assumptions, and which errors stop a run versus allow partial results. Never turn unavailable or invalid evidence into a valid zero or default classification.
2. **Keep the core independent of the wizard.** Put classification rules, calculations, normalization, and aggregation in callable functions/services that do not import widgets or access global `iface`. Keep UI, Processing parameter handling, QGIS project mutation, and layer/file conversion at the edges. Prefer plain data structures at the boundary between domain logic and QGIS adapters.
3. **Use one execution path.** The wizard's analysis task and Processing algorithm
   both call the shared `run_workflow(parameters, feedback)`. The wizard captures
   inputs and presents results; Processing adapts toolbox/batch/model parameters.
   Keep validation, retrieval, classification and publication in that shared
   workflow, as documented in the architecture overview.
4. **Validate before expensive work or output mutation.** Check required layers and providers, validity, geometry types and emptiness, expected fields and compatible field types, CRS transforms, output destinations, and overwrite behavior. Identify optional layers and explain which outputs become unknown or partial when they are absent.
5. **Make the run observable.** Report meaningful progress, source/layer identity, skipped-feature counts, coverage, and the phase that failed. Preserve diagnostic details and run parameters in logs or run metadata. Keep user-facing errors short and actionable, with a next step where possible.
6. **Add tests at the right boundaries.** Cover pure rules with ordinary unit tests, QGIS-specific adapters with PyQGIS integration tests and tiny local fixtures, and the real shared Processing workflow end to end. Add a manual GUI acceptance check for plugin lifecycle and user interactions. See [Testing](#testing-and-debugging).
7. **Check both languages and package behavior.** Review all user-visible strings, exercise Finnish and English, then smoke-test the built plugin ZIP in the declared QGIS version, including load, Processing registration, run, and unload.
8. **Reconcile maintained documentation.** Follow [specification maintenance](specifications.md): update final user stories and functional behavior in `docs/specs/`, technical contracts/design in `docs/architecture/`, and affected manuals. Link those outcomes from the working `.scratch/` spec and preserve pending acceptance checks explicitly.

## Architecture and QGIS practices

- Keep the plugin entry point and wizard thin. Processing is the toolbox, batch
  and modeler entry point; the wizard's task calls the same application workflow.
- Do not make the analysis depend on widget state, global project state, or `iface`. Pass required inputs, parameters, feedback, and output destinations explicitly.
- Put provider-specific field mapping and source retrieval in adapters. Convert input schemas into a normalized representation once; keep source metadata, dates, and identifiers for provenance.
- Keep stable IDs, machine-readable status values, field names, and configuration keys language-neutral. Translate presentation labels only.
- Make CRS transformations explicit. Calculate areas and distances in an appropriate projected CRS and state the measurement method and units. Do not assume layers share a CRS.
- Define how invalid geometries are handled: reject, repair under an explicit policy, or skip and report. Preserve enough source identifiers to trace each result back to its input.
- Make overlaps, rule precedence, buffers, nulls, partial coverage, and unknown classifications explicit in code and documentation. Do not silently infer completeness from an empty query result.
- Preserve input data. Write results to clearly named outputs, and avoid deleting or replacing user data as a side effect. Prevent partially written outputs from being mistaken for successful results; validate writes and clean up failed temporary outputs.
- Use Processing feedback for progress, information, cancellation, and recoverable feature errors. Raise `QgsProcessingException` for conditions that make the run unusable. At the wizard boundary, log the full exception and show a concise message that identifies the failed step or source. Do not swallow exceptions or use broad catches to continue with fabricated results.
- Preserve the existing thread boundary: the wizard captures worker-safe inputs
  and constructs worker-owned providers; the shared workflow runs synchronously
  in its caller's execution context. Keep widgets, `QgsProject` and GUI-owned
  layers in the main thread, and return project/UI updates there. Read and test
  the [documented worker boundary](../architecture/overview.md#qgis-and-thread-boundary)
  before extending asynchronous work.
- Follow QGIS APIs and compatibility supported by the plugin's declared version. Keep the Python interpreter, PyQGIS/Qt libraries, and debug environment aligned with the installed QGIS runtime.

## Errors, logging, and debugging

Use an explicit error policy:

| Condition | Expected behavior |
| --- | --- |
| Invalid required input, missing required field, impossible CRS transform, or unwritable output | Stop before publishing results; report the layer/path and the corrective action. |
| Optional source unavailable or incomplete | Continue only where the feature specification defines partial behavior; mark affected outputs unknown/not available and report the limitation. |
| Bad individual feature that can be excluded safely | Report its source ID and reason, count skipped features, and continue only if exclusion is part of the documented policy. |
| Unexpected exception or internal invariant failure | Stop; preserve traceback and run context in diagnostics; show a concise error to the user. |
| User cancellation | Stop promptly at safe checkpoints and leave no output that appears complete. |

Before changing diagnostics, read and follow the
[logging contract](../architecture/operations.md#logging). It owns channel
payloads, destinations, rotation, handler lifecycle and source rationale.

- Keep detailed technical diagnostics separate from aggregate business-action
  records. Use module loggers under the plugin namespace; configure owned
  handlers once per load and close them on unload. Preserve the shared root logger.
- Use Processing feedback for progress/recoverable messages, concise translated
  UI errors for corrective action, and `logger.exception()` with run/stage context
  for unexpected failures. Aggregate repeated feature problems and cap ID samples.
- Keep credentials and unnecessary personal/source data out of both channels;
  business-action records exclude paths, project/layer names and feature data.
  A logging failure must not hide the original error or prevent normal use.
- Reproduce defects with the same QGIS runtime and local fixtures; record the
  reload/debug setup and preserve a traceback where relevant.

## Testing and debugging

Use the [development guide](../architecture/development.md) for commands and
runtime setup. For a read-only review, report compliance and gaps without claiming
tests were executed. For code changes, run the relevant checks below and the
required bilingual/package checks. Documentation navigation alone needs link and
contract-consistency checks; changes to packaged manuals or resources also need
the affected help/package checks. Report checks performed and untested areas in
the task result. Use the [personal manual checklist](../testing/manual-acceptance.md)
for GUI checks and its lightweight workflow.

Keep tests deterministic and independent of live data services wherever possible.
Use tiny checked-in or generated local fixtures; do not mutate source fixtures in place.

All eight configured analysis layers are required. Numeric metric gaps may
produce partial/unavailable indicators; required-source failures stop publication.
Use [WF-07](../specs/workflow.md#wf-07-failure-cancellation-and-observability)
and the [source contract](../architecture/data-sources.md) when choosing fatal
and partial-data cases.

Test the following layers:

1. **Pure unit tests:** rule evaluation, schema normalization, classification precedence, aggregation, unit conversions, missing-value policies, status generation, and error categorization. These tests should run without launching QGIS wherever the logic can be expressed without PyQGIS.
2. **PyQGIS integration tests:** layer/provider adaptation, geometry operations, CRS transforms, Processing parameter validation, output writing, and result metadata using a temporary directory and small GeoPackage fixtures.
3. **Workflow end-to-end tests:** exercise the shared workflow through the
   Processing algorithm and check the wizard's task boundary when affected.
   Assert semantically important output layers, attributes, CRS/units,
   coverage/status fields, workbook contents and failure messages. Include at
   least one success path and representative fatal and partial-data paths.
4. **GUI acceptance checks:** use the [manual checklist](../testing/manual-acceptance.md) in the supported QGIS runtime to inspect the installed plugin, Finnish/English interactions, saved outputs and failure handling. These checks supplement deterministic automated tests.

Include regressions for empty input, null and invalid geometry, multipart features, missing or renamed fields, differing CRSs, no-match and partial-coverage cases, unavailable providers, cancellation, and output-write failures. For spatial results, compare meaningful attributes and geometries with suitable tolerances; avoid byte-for-byte comparisons of GeoPackages where metadata or ordering can vary.

Do not make routine tests depend on external WFS availability. Use controlled local fixture data or recorded responses for service-related tests, and keep any live-service smoke check separate from the deterministic test suite. When a defect is fixed, add a small regression case at the narrowest layer that would have caught it.

## Internationalization and localization (Finnish and English)

Use **internationalization (i18n)** to keep code ready for multiple languages and **localization (l10n)** for Finnish and English wording and regional presentation. The current `i18n.py` text catalog and `tr(language, key, ...)` helper are the project's translation mechanism; extend them consistently unless the implementation deliberately migrates to QGIS/Qt translation catalogs with build and packaging support.

- Resolve the presentation language through `selected_language()`, which reads `QgsApplication.locale()`: Finnish QGIS uses Finnish; all other or unavailable languages use English. Apply this to the wizard, menus, Help/About, Processing and new outputs. QGIS is the sole language setting for the plugin.
- Put every user-visible string in the translation mechanism: dialog labels, buttons, menus, tooltips, validation messages, error summaries, Processing labels/help, progress text, output sheet/column labels, and plugin metadata shown to users. Avoid untranslated strings embedded in analysis, exporters, or exception handlers.
- Keep translation keys and internal values stable; do not use translated labels as identifiers, field names, serialized values, or control-flow inputs.
- Format messages with named placeholders, not string concatenation. Ensure both language entries define the same placeholders. Use translation-aware plural forms when reporting counts; do not construct English-only plural grammar in code.
- Keep dates, numbers, decimal separators, and units explicit and appropriate to the selected locale. Do not localize machine-readable timestamps, field IDs, or interchange values.
- When refreshing the QGIS application language, refresh all visible text and help, including source statuses and errors. Keep each analysis run's resolved language consistent through its messages and outputs.
- Test that every used key has Finnish and English text, formatting succeeds with representative placeholder values, and critical flows display the selected language in both automated tests and GUI acceptance.
- If switching to `.ts`/`.qm` catalogs, use the Qt Linguist/QGIS-supported workflow available in the targeted QGIS runtime and include generated catalogs in the package. Qt's translation guidance recommends marking translatable text, using placeholders, handling plural forms, using regional number/date/currency formats, and preparing for dynamic language changes; confirm exact APIs against QGIS's bundled Qt/PyQt version. [Qt writing source code for translation](https://doc.qt.io/qt-6/i18n-source-translation.html) · [Qt internationalization overview](https://doc.qt.io/qt-6/internationalization.html)

## Review evidence

For each changed boundary, check the required workflow and relevant contracts
above. Tie findings to the violated requirement and verification needed; summarize
which deterministic, bilingual, packaged and interactive checks were performed
or remain untested in the task result. Keep substantive limitations in their
maintained owners and use the personal checklist workflow for manual checks.

## Related project documentation

- [Operations](../architecture/operations.md) — adopted development, logging and bilingual help design with primary sources.
- [Architecture overview](../architecture/overview.md) — implemented workflow, module ownership, result semantics and limitations.
- [Remaining verification](../open-questions.md) — unresolved evidence, acceptance and distribution checks.
- [Plugin README](../../qgis_plugin/README.md) — current supported version, installation, workflow, and interpretation limits.
