# QGIS plugin development and debugging

**Savonia - Responsible Forest Planning is Antti Kajanus's unfinished personal
learning prototype, based on limited understanding and personal assumptions.
Neither it nor its results are backed, endorsed, finalized, or approved by
Savonia in any form.** Implementation and test completion here describe this
prototype only; see the [project context](../../README.md).

This guide owns setup, reload, debugger, test and packaging instructions for the Savonia - Responsible Forest Planning plugin. Run commands from the repository root unless stated otherwise. The plugin targets **QGIS 4.2.3 and newer 4.x releases**, as declared in [metadata.txt](../../qgis_plugin/savonia_responsible_forest_planning_tool/metadata.txt) (`4.2.3` minimum, `4.99` maximum). QGIS 4.2.3 is the verification baseline. Run the suites and packaged load/Processing/unload checks on each newer release before recording it as verified; the metadata range permits installation without establishing future runtime compatibility.

This guide owns repeatable development and verification procedures. Record the
tested build/runtime, locale, date and outcome when executing them; current
outstanding checks belong to the [verification register](open-questions.md).
Automated headless/offscreen checks do not establish interactive acceptance.
The maximum uses QGIS's major-version-plus-`.99` convention. QGIS documents [plugin metadata ranges](https://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/plugins/plugins.html#metadata-txt)
separately from [runtime testing](https://docs.qgis.org/4.2/en/docs/developers_guide/unittesting.html)
and [Processing algorithm tests](https://docs.qgis.org/4.2/en/docs/developers_guide/processingtesting.html).

## Python linting

[Pylint configuration](../../pyproject.toml) covers the plugin, regression tests
and development scripts. Install the pinned
[development dependencies](../../requirements-dev.txt) into the QGIS Python
environment's user site, then run from the repository root:

```powershell
& 'C:\Program Files\QGIS 4.2.3\bin\python-qgis.bat' -m pip install --user -r requirements-dev.txt
& 'C:\Program Files\QGIS 4.2.3\bin\python-qgis.bat' -m pylint qgis_plugin scripts
```

Use the configured QGIS launcher rather than a plain Python installation so
PyQGIS and Qt imports resolve. Pylint may inspect the known `qgis` and `PyQt6`
compiled extensions, as described in its
[extension guidance](https://pylint.pycqa.org/en/latest/user_guide/messages/error/no-member.html).
Missing imports and member errors remain enabled. The configuration adds the
plugin and test-fixture import roots and accounts for the existing unittest
mixin and dynamically assigned HTTP fixture attributes.

The initial policy enables fatal/error diagnostics and selected correctness
warnings, including mutable defaults, duplicate keys, bare exception handlers
and unreachable code. Formatting, naming, complexity and the remaining warning
checks are outside this initial policy. Any enabled diagnostic fails the command;
no numeric score threshold or successful-exit override is used. Recursive
discovery covers tests without `__init__.py`; generated archives, bytecode,
virtual environments and local scratch work are excluded. To lint one file,
replace `qgis_plugin scripts` with its path. Editor integrations must use the
same QGIS runtime and repository working directory. Development dependencies
remain outside the plugin package.

CI uses this same policy and QGIS 4.2.3 launcher. Any enabled diagnostic fails
the quality job and prevents its dependent release job from running. No extra
warning/style rules are introduced by CI enforcement.

## Local provider references

Populate `docs/references/service-metadata/` once before investigating service contracts:

```powershell
& 'C:\Program Files\QGIS 4.2.3\bin\python-qgis.bat' scripts/download_references.py
```

Any Python 3.10+ installation works; the script uses only the standard library.
Agents can then read capabilities, eight layer schemas and provider PDF/XLSX
documentation locally. The cache is ignored by Git. Its versioned manifest,
refresh/filter options, optional `SYKE_USER_ID`, provenance and failure behavior
are documented in [reference instructions](../references/service-metadata/README.md).
Maintain this manifest alongside the [source registry contract](data-sources.md)
when endpoints or required layers change. The downloader deliberately does not
import the plugin or require QGIS to read development reference material.

Run tooling checks separately from plugin tests with Python 3.10+ and Git
available on PATH. They cover HTTP fixtures and release-version Git fixtures:

```powershell
python -m unittest discover -s scripts/tests -v
```

The downloader checks file formats; representative feature values and provider
completeness require separate checks. Local retrieval details remain in ignored
`retrievals.json`.

## Recommended setup: a dedicated development profile

A separate QGIS profile keeps development settings away from normal work. See
the QGIS [profile guidance](https://docs.qgis.org/testing/en/docs/user_manual/introduction/qgis_configuration.html#working-with-user-profiles),
[plugin lifecycle](https://docs.qgis.org/4.2/en/docs/pyqgis_developer_cookbook/plugins/index.html)
and [reload/debug guidance](https://docs.qgis.org/4.2/en/docs/pyqgis_developer_cookbook/plugins/ide_debugging.html).

Keep the complete checkout, including repository `docs/help/`, available at its
original location. The source-linked plugin resolves its manuals there. Use the
junction or `QGIS_PLUGINPATH` setup below for development; copying only
`savonia_responsible_forest_planning_tool` into a profile omits those manuals.
For an installed copy, follow the [Plugin installation guide](../../qgis_plugin/README.md#plugin-installation).

1. In QGIS, open **Settings > User Profiles > New Profile...** and create a profile such as `Savonia development`.
2. Switch to that profile and open **Settings > User Profiles > Open Active Profile Folder**. Keep this folder open; it is the profile QGIS is currently reading.
3. Under the profile folder, create `python\plugins` if it does not already exist.
4. In PowerShell, create a directory junction from that profile's plugins directory to the plugin source in this checkout. Set `$profilePlugins` to the `python\plugins` folder you just opened:

   ```powershell
   $pluginSource = (Resolve-Path ".\qgis_plugin\savonia_responsible_forest_planning_tool").Path
   $profilePlugins = "C:\path\to\the\active\profile\python\plugins"
   $pluginLink = Join-Path $profilePlugins "savonia_responsible_forest_planning_tool"
   New-Item -ItemType Junction -Path $pluginLink -Target $pluginSource
   ```

   Run this from the repository root. Create the junction only when `$pluginLink` does not already exist. The junction lets QGIS import the files directly from the checkout, so edits do not need to be copied into the profile.
5. Close QGIS and reopen it with the `Savonia development` profile (or the development profile you created) so it discovers the linked plugin.
6. Open **Plugins > Manage and Install Plugins...**. Find **Savonia - Responsible Forest Planning** under **Installed** and check its checkbox to enable it. The plugin is ready to use after this step; creating the junction alone does not activate it.

Alternatively, set `QGIS_PLUGINPATH` to the directory containing `savonia_responsible_forest_planning_tool` before starting QGIS. QGIS must inherit that environment variable when it launches. Then reopen QGIS and enable the plugin as described in steps 5–6. A junction in the active development profile is usually easier to verify and keep in place.

## Load the plugin and reload edits

With the plugin enabled in the development profile:

1. In **Plugins > Manage and Install Plugins...**, install **Plugin Reloader** once. It is a separate helper plugin.
2. Edit and save files in `qgis_plugin\savonia_responsible_forest_planning_tool`.
3. Use Plugin Reloader's reload action for **Savonia - Responsible Forest Planning**. The plugin remains installed; you do not need to uninstall and reinstall it after code edits.

If the plugin does not appear, confirm that QGIS is using the development profile, that the junction points to the package folder (the folder containing `metadata.txt` and `__init__.py`), and that there is only one copy of this package on QGIS's plugin search paths.

Reloading executes the plugin lifecycle again, but it cannot guarantee that every process-wide Python or Qt reference has been discarded. The plugin's `unload()` should undo plugin-owned setup: remove menu and toolbar actions, unregister its Processing provider, stop owned timers, and disconnect signal handlers. If a reload fails or behavior remains stale after cleanup, restart QGIS to start with a clean Python process.

## Debug failures in QGIS

1. Open **View > Panels > Log Messages** and select the plugin's tab. Check the first error and traceback from the failed load or run.
2. Open **Plugins > Python Console** to inspect the live QGIS Python session. For example, `qgis.utils.plugins` shows the plugin instances QGIS currently has loaded. Use the console to inspect state and reproduce a narrow failure; the console shares the running QGIS process and its PyQGIS environment.
3. For breakpoints, configure the IDE to use the Python, PyQGIS, Qt and PyQt runtime bundled with the QGIS release being tested. The commands below use the QGIS 4.2.3 baseline. A regular system Python interpreter usually does not have the QGIS runtime available.
4. After changing code, reload with Plugin Reloader and repeat the same steps. If errors only appear on the second load, check `unload()` and initialization for duplicate actions, signal connections, timers, or Processing registrations.

Keep the error's traceback, the QGIS version, and the steps and inputs that reproduce it when recording a defect. Do not treat an empty result or missing online source as a successful run; check the plugin's reported source readiness and coverage as well.

## Deterministic indicator and source regression checks

The source-field and pure grid-indicator tests use Python's standard `unittest`. From the repository root,
run the pure checks without QGIS using a configured Python interpreter:

```powershell
python -m unittest discover -s qgis_plugin/tests -v
```

For QGIS integration, use the declared runtime's configured Python launcher:

```powershell
& 'C:\Program Files\QGIS 4.2.3\bin\python-qgis.bat' -m unittest discover -s qgis_plugin/tests/qgis -v
```

The integration suite runs headlessly with generated polygon data and a tiny WFS
fixture bound to a random loopback port. It calls the shared Processing algorithm
with real WFS providers and checks GeoPackage/workbook results and failure messages
in Finnish and English. It requires local loopback access but no online services.
The fixture implements only the WFS operations needed by these tests. Existing
small GML2 scenarios use WFS 1.0 as test transport; they do not establish support
for legacy production services. Dedicated WFS 2.0/GML 3.2 scenarios construct
layers through the production URI builder with fresh unprimed providers, verify
paged retrieval and successful empty responses, and fail a later page. Analysis
pages carry AOI bounds; QGIS may separately probe geometry with `COUNT=1` during
provider construction. No live provider is required.

Shared scenarios and source-field setup leave WFS providers fresh by default;
the shared production workflow owns AOI-bounded initialization and retrieval.
The explicit `prime=True` cache and selected-feature scenarios use an empty
feature-ID filter, the AOI rectangle and a zero-result limit, then close that
iterator without reading features. Empty IDs and a zero limit alone do not guarantee that QGIS
will avoid starting a download, so priming must also carry spatial bounds.
Setup must not assume an unrestricted first read is empty: hosted QGIS returned
configured records where the local runtime returned none. Keep feature-content
assertions in workflow/output tests. The regressions in
`test_workflow_contracts.py` and `test_source_field_workflow.py` reproduce the
populated-read behavior, assert bounded initial requests and check that source
values reach published outputs, including Finnish/English source-field runs.

### Regression seams

| Contract | Tests and assertions |
| --- | --- |
| Pure tier policy, CL-02/03 | `tests/test_classification.py`: all 32 trigger combinations, exact matched rules/IDs, missing dependencies, positive-match precedence and uninterpretable records. |
| Spatial classification, CL-01/03 | `tests/qgis/test_classification_geometry.py`: below/at/above 1 m², shared edges/points, protected strips, Section 10 parent promotion, neighboring stands, piece-local IDs in both source orders and conserved geometry. |
| Selection/preflight/protocol, WF-03/04/06/07 | `tests/qgis/test_workflow_contracts.py`: captured source geometry/attributes despite later selection/service changes, equivalent worker/Processing values, selection metadata, invalid inputs and aggregate readiness errors before retrieval, untouched existing output bytes, WFS 2.0 paging and later-page failures. |
| Paired publication, WF-07 | `tests/qgis/test_publication_failures.py`: later GeoPackage-layer and required-style failures, cancellation after workbook creation, paired cleanup, and original error preservation when deletion fails. Existing grid workflow checks cover cancellation after GeoPackage writing and workbook-write failure. |
| Wizard, WF-01/05 and IO-06 | `tests/qgis/test_wizard_completion.py`: localized failure/cancellation recovery, reopening failure, exact readable counts and feature iteration for 18 filtered views plus eight snapshots, visibility, prior-run retention, and cancellation/detachment on unload. |
| Logging, WF-07 | `tests/qgis/test_logging_contract.py`: owned handler reload/unload, root preservation, rotation settings, aggregate JSON events correlated by run ID, technical-only tracebacks, and directory/file-open failures. |

`workflow_fixture.py` owns shared source records and Processing scenarios;
`ui_fixture.py` supplies real Qt widgets behind a small QGIS interface adapter.
These helper modules contain no discoverable tests. Inject failures at provider,
writer, filesystem or UI seams; keep numerical expectations independent of
implementation constants. Headless checks do not establish desktop acceptance.

Grid setup checks use the same local WFS boundary and real QGIS 4.2.3 layer trees
and rendering APIs. They cover the eighth required source, provider-backed fields
and stable cell IDs, explicit `GRIDCELLS` Processing input, repeated setup and
Finnish/English relabeling, preservation of unmanaged references, and bottom grid
placement. Scale checks include visible 1:200/1:300 and hidden 1:300.001/1:500.
QGIS excludes an exactly equal minimum scale; setup uses a `1e-6` denominator
margin for inclusive 1:300. This is display only and is absent from worker inputs.

Calculation/workflow acceptance covers exact boundary intersections (including
0.5 m²), projected CRS transforms, cell duplicates/conflicts, stand overlaps
(shared edges, 0.5 m² and exactly 1 m² accepted; greater than 1 m² rejected),
AOI dissolution, empty/partial coverage, metric-specific sufficient statistics,
integer half-up age rounding and null preservation. Compare reopened artifacts
by semantic values with tolerances rather than GeoPackage bytes. Keep grid and
stand volume denominators separate; never aggregate rounded age percentages.

To check an extracted plugin ZIP, set `RESPONSIBLE_FOREST_PLANNING_TEST_PLUGIN_ROOT` to the directory
containing the extracted `savonia_responsible_forest_planning_tool` folder and run
the integration command in a new Python process. The test code remains outside
the distributable plugin. GUI acceptance and live-source smoke checks remain
separate from these deterministic checks.

Tests also accept `SAVONIA_TEST_PLUGIN_ROOT` for existing local commands. The
`RESPONSIBLE_FOREST_PLANNING_` variable takes precedence when both are set. CI
uses the preferred variable. Plugin folders and archive names remain unchanged.

## Check packaging separately

Wizard spacing procedure: in Finnish and English,
open the wizard both docked and floating, then resize it taller and narrower.
The heading, description, analysis-area choices and output folder should stay
together at the top with normal spacing; extra height should appear below the
output folder, with the action buttons at the bottom. Check each analysis-area
mode and wrapped status text. The offscreen regression is
`tests/qgis/test_wizard_layout.py`, included in the integration suite above.

Wizard toolbar icon procedure: in Finnish and English,
compare setup, redock, Help and About with QGIS's native panel toolbars, such as
Identify Results. They use QGIS's dock toolbar icon size (`iface.iconSize(True)`)
in both docked and floating mode. Change QGIS's toolbar icon size and reopen the
plugin after a reload to verify the new size is used. Automated checks exercise
16, 24 and 32 pixel dock icons and both dock modes. This is a presentation-only
change; analysis inputs, outputs, CRS, units and error behavior are unaffected.

The linked development checkout is for fast iteration. Use a ZIP install when checking the distributable package:

- Run `./qgis_plugin/package.ps1` in Windows PowerShell from the repository root to build or refresh the ZIP using the version already in `metadata.txt`. This is the ordinary installation and development packaging command; it preserves the metadata version and replaces the ZIP for that version.
- The script includes the source package and copies both repository manuals from `docs/help/` into the installed package's `docs/help/`, adjusting local resource links. Keep the full checkout when building.
- **Release maintainers:** `./qgis_plugin/package.ps1 -BumpMinor` increments the minor version in `metadata.txt`, resets the patch to zero and writes a ZIP. Use the switch only when intentionally preparing a new version; it edits metadata before building, so an archive failure can leave the increment in place. Packaging errors stop the command and remove an incomplete ZIP.
- In QGIS Plugin Manager, use **Install from ZIP** and select the generated file under `qgis_plugin\dist`. For a clean acceptance check, use a separate profile so a previously installed copy cannot be confused with the development source.

For a release or final acceptance check in QGIS 4.2.3, verify that the ZIP loads, the main plugin toolbar opens the wizard, and setup works from both the wizard toolbar and plugin menu (including with the wizard closed). In Finnish and English, check that setup is first in the docked and floating wizard toolbar, separated from redock/Help/About, with a translated tooltip and accessible name. Verify that the Processing algorithm is available, the shared workflow reports failures clearly, and unloading/reloading does not duplicate actions or provider entries.

### Result field organization checks

The result form groups and table columns follow the
[per-polygon field reference](output-schema.md#per-polygon-fields). Regression
checks verify field/value alignment, source-first Finnish/English labels,
persisted GeoPackage form groups and area explanations, and the matching
workbook/documentation order. These checks are part of the
[integration suite](../../qgis_plugin/tests/qgis/test_result_field_organization.py).
Build the ZIP with `./qgis_plugin/package.ps1`, extract it and run the suites
against that copy using `RESPONSIBLE_FOREST_PLANNING_TEST_PLUGIN_ROOT` as described above.

For desktop acceptance, install the ZIP in a separate profile, inspect
table/form/Identify labels and nulls in both languages, reopen the GeoPackage,
and inspect the workbook in Excel.

<a id="grid-indicator-manual-gui-acceptance--pending"></a>

### Grid-indicator manual GUI acceptance

Execute these steps in both languages and record the build, locale, date and
result. [Current status](open-questions.md#interactive-acceptance) is maintained
separately; this list is the reusable procedure.

- Install the current-version ZIP in a separate QGIS 4.2.3 profile; load,
  open/reopen the wizard, check Processing registration, reload and unload.
- In Finnish and English, run setup repeatedly and after a language change;
  confirm exactly one grid at the bottom of References, unchanged relative order
  of other references, and Results above References above Basemaps.
- Inspect the grid at 1:200, 1:300 and 1:500; confirm the first two render
  and the last does not. Run the same local fixture at near/far canvas scales
  through wizard and Processing and compare calculations and captured snapshots.
- Inspect both total-volume aliases/columns, deciduous volume,
  integer age shares/coverage, partial metric denominators/lower bounds,
  and source dates/reporting-area notes in the result and workbook in both languages.
- Exercise cancellation and representative required-source/geometry failures;
  verify actionable localized messages and no apparently complete partial outputs.

## Automatic GitHub builds and releases

The [build and release workflow](../../.github/workflows/build-and-release.yml)
runs after each push to main and for pull requests targeting main. Main builds
publish the next minor release after tests pass; pull requests expose only an
installation ZIP artifact. The [distribution contract](distribution.md#github-builds-and-releases)
owns version selection, release tags, permissions, queuing and recovery.

Download `savonia_responsible_forest_planning_tool-<version>.zip` from
[Releases](https://github.com/anttikajanus/savonia-responsible-forest-planning-tool/releases)
and install it through QGIS Plugin Manager. The release tag includes its updated
metadata and can be rebuilt with `./qgis_plugin/package.ps1` without another bump.

For recovery, open **Actions → Build and release QGIS plugin**, select the failed
main run and choose **Re-run failed jobs**. To start a build explicitly, choose
**Run workflow** with branch `main`. A rerun reuses that source's existing release
tag/version, completes an unfinished draft, or leaves a published release intact.
If the job cannot push tags or publish, check that repository/organization policy
permits the release job's `contents: write` token and its release tags.

Hosted CI has two check names: `Test and build installable ZIP` and
`Pylint and QGIS 4.2.3 integration`. The first runs tooling and pure suites plus
packaging/extracted-ZIP checks. The second installs the versioned QGIS 4.2.3
Windows MSI after verifying the published SHA-256, checks the runtime version,
installs `requirements-dev.txt` into QGIS Python's user site, and runs Pylint
and the QGIS integration suite. Integration runs use `QT_QPA_PLATFORM=offscreen`
against both source and the actual ZIP downloaded from the build job. Neither
suite uses live analysis services. The quality job has read-only permissions;
only the existing release job can publish. Both jobs must succeed before a
main release starts. Failed installs retain `qgis-install.log` as a diagnostic
artifact when the installer created it.

Continue Finnish/English desktop acceptance locally as documented here.
Offscreen CI does not establish interactive acceptance or compatibility with
newer QGIS releases. The [verification register](open-questions.md#acceptance-and-distribution)
records hosted execution and repository-setting checks separately.

### Required merge checks

Workflow jobs run on pull requests, but preventing a merge also requires active
GitHub branch protection or a ruleset for `main`. Require both exact check names
above and require the branch to be up to date before merging. Keep existing
protection rules. GitHub documents
[required status checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches#require-status-checks-before-merging).

The [main quality ruleset](../../.github/rulesets/main-quality.json) is an
API-ready definition with those two checks and no bypass actors. A checked-in
JSON file does not activate repository settings. After the updated workflow
has run successfully, a repository administrator can create the additional
ruleset from the repository root:

```powershell
gh api --method POST repos/anttikajanus/savonia-responsible-forest-planning-tool/rulesets --input .github/rulesets/main-quality.json
```

Create it once; inspect the existing repository rulesets before applying it
again. If an equivalent ruleset already exists, update that rule through
GitHub settings instead of creating a duplicate. This adds requirements without
replacing existing protection. The [verification register](open-questions.md#acceptance-and-distribution)
records activation and hosted enforcement separately from the checked-in
workflow and ruleset.

## Help and credits verification

Edit the canonical manuals in [English](../help/manual_en.html) and
[Finnish](../help/manual_fi.html) under the repository's `docs/help/`.
Source-linked development resolves these files directly. Both packaging modes
read this directory and bundle the manuals under the plugin's `docs/help/`,
adjusting relative legal-resource links to stay inside the installed package.
Keep the repository layout when copying the packaging script to a test directory.

The resource resolver is independent of QGIS and widgets. Run its standalone tests
and the disposable-copy packaging checks with Python, then run the complete
suites with the configured QGIS 4.2.3 launcher shown above. The packaging checks
exercise both modes, including the version-incrementing path only in a temporary
copy; they leave working metadata and generated source caches intact.

For extracted-package verification, set `RESPONSIBLE_FOREST_PLANNING_TEST_PLUGIN_ROOT` to the directory
containing the extracted package and run each suite in a new Python process. All
plugin imports in the regression suites honor that root. The packaging-script
tests still exercise the checkout's scripts and source package; the Processing
help tests copy the selected package to a separate temporary ZIP installation.
Keep these distinctions when reporting installed-package coverage.

Check Finnish and English QGIS locales and English fallback for other QGIS
languages. Check that the wizard follows QGIS's language, Help/About with the dock
closed, QGIS language refresh, detached controls, Processing help, full offline
legal texts, browser failures, and unload/reload cleanup. Automated offscreen
widget checks supplement interactive desktop acceptance. Record acceptance
outcomes against the [register](open-questions.md#interactive-acceptance).

For desktop language acceptance, set QGIS's application language to Finnish,
restart as prompted, and check the wizard, global Help/About and Processing.
The wizard title and controls should be localized, with no personal learning
prototype banner or prototype suffix on working tool labels. Open About/info
and verify the personal prototype notice remains there; also check Plugin
Manager metadata and the repository documentation for that notice.
Repeat with English and an unsupported language, which should use English.
Confirm that QGIS's application language is the sole language setting for the
plugin.

## Related guidance

- [QGIS implementation, testing, and localization guidance](../agents/qgis.md)
- [Development, logging and bilingual help design](operations.md)
- [Plugin installation and workflow](../../qgis_plugin/README.md)
