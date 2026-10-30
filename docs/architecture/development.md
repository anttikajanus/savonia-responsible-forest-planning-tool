# QGIS plugin development and debugging

**Savonia - Responsible Forest Planning is Antti Kajanus's unfinished personal
learning prototype, based on limited understanding and personal assumptions.
Neither it nor its results are backed, endorsed, finalized, or approved by
Savonia in any form.** Implementation and test completion here describe this
prototype only; see the [project context](../../README.md).

This guide owns setup, reload, debugger, test and packaging instructions for the Savonia - Responsible Forest Planning plugin. Run commands from the repository root unless stated otherwise. The plugin targets **QGIS 3.44 and newer 3.x/4.x releases**, as declared in [metadata.txt](../../qgis_plugin/savonia_responsible_forest_planning_tool/metadata.txt) (`3.44.0` minimum, `4.99` maximum). The verification baselines are QGIS 3.44.0 and 4.2.3. The continuous metadata range also permits intervening 4.0/4.2 releases; run the suites and packaged load/Processing/unload checks on each additional target before recording it as verified.

This guide owns repeatable development, automated verification and packaging
procedures. The [manual checklist](../testing/manual-acceptance.md) owns
interactive steps and expected results for personal use. Current
outstanding checks belong to the [verification register](../open-questions.md).
Automated headless/offscreen checks do not establish interactive acceptance.
The maximum uses QGIS's major-version-plus-`.99` convention. QGIS documents [plugin metadata ranges](https://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/plugins/plugins.html#metadata-txt)
separately from [runtime testing](https://docs.qgis.org/4.2/en/docs/developers_guide/unittesting.html)
and [Processing algorithm tests](https://docs.qgis.org/4.2/en/docs/developers_guide/processingtesting.html).

## Local check runner

Use the Windows entry point for the source checks, or include package validation:

```powershell
./scripts/check.ps1
./scripts/check.ps1 -Package
./scripts/check.ps1 -Checks tooling,unit
./scripts/check.ps1 -Checks qgis -QgisPattern test_parcel_reference.py
./scripts/check.ps1 -Checks qgis -TimeoutSeconds 900
```

[check.ps1](../../scripts/check.ps1) selects a plain Python executable from PATH,
falling back to the interpreter bundled with the selected QGIS installation.
`-Python` selects an explicit executable. Tooling and unit checks run directly
with that interpreter; lint and integration checks use `-QgisPython` (default:
`QGIS_PYTHON`, then the baseline launcher below). Python 3.10+ is required.
Plain Python need not be a separate installation: calling the bundled executable
directly keeps tooling out of the QGIS launcher's modified environment.

[check.py](../../scripts/check.py) checks Git when tooling is selected and the
isolated QGIS runtime when lint or integration is selected, before starting
test suites. When lint is selected, it also imports Pylint and Astroid through
the selected QGIS launcher, reports their versions and module paths, and checks
the stable versions against `requirements-dev.txt`. An unsupported or missing
tool stops preflight with a PowerShell upgrade command for that launcher.
Import details appear on the console and in `preflight-lint.log`; an inherited
`PYTHONPATH` override is not evidence of which tools the launcher imports.
Selecting tooling also runs [the parser probe](../../scripts/check_tooling_environment.py)
through the selected plain Python executable before test discovery. It verifies
`markdown_it.MarkdownIt` and `yaml.safe_load` with basic parsing, reporting the
interpreter and imported file paths on the console and in `preflight-tooling.log`.
Missing/broken imports, incomplete namespace packages and unusable parsers stop
all selected suites. Failure diagnostics probe source-file readability, retain
the original exception, and give an install command using that interpreter and
`requirements-dev.txt`. Existing-package failures also point to the file-access
troubleshooting below. Checks do not install packages or change permissions.
To run the probe alone, use `python scripts/check_tooling_environment.py`.
Missing dependencies or failed checks return nonzero and identify
the failed stage. Complete stdout/stderr goes to separate UTF-8 logs under a
unique ignored `.local/checks/<UTC timestamp>-<id>/` directory; the console shows
elapsed times, failing unittest names and a short failure tail. If a crash or
timeout prevents unittest's failure report, the summary includes the last test
reported when available. `failure.log` retains the same failure summary.
`-LogsDir` changes the parent directory;
use `.local/` for repository-local output. Directory ownership is defined in the
[local artifact guidance](../agents/issue-tracker.md#local-development-artifacts).
Selected checks run in order: tooling, unit, lint, QGIS. Source checks clear
inherited installed-plugin overrides so they always exercise this checkout.

Each subprocess has a 600-second deadline, including prerequisites, lint and
packaging. Set `-TimeoutSeconds` (Python: `--timeout`) to a positive finite
number of seconds to override it for every stage. A timeout stops the process
tree, returns nonzero and preserves existing output; Windows batch launchers'
Python children are stopped before isolated test storage is removed. Process
termination diagnostics share the stage log. Python fault handling is enabled
in check subprocesses so fatal native faults can retain Python stacks in logs.

`-Package` invokes the existing current-version packaging command, extracts its
ZIP into the run directory, and repeats the selected unit and QGIS suites on
that installation. It preserves the metadata version. The same QGIS pattern
applies to source and installed checks. The runner also works as
`python scripts/check.py --help`; detailed/direct commands remain below.

On Windows, workspace-local dependencies unpacked under another execution
account can retain temporary-directory permissions. An unreadable package
`__init__.py` may appear as a namespace package and cause `cannot import name`
with `unknown location`, even when the directory and package metadata exist.
Compare `Get-Acl` and direct file reads under the account running the failed
check. For a disposable local dependency directory whose parent already has
the intended workspace permissions, restore inheritance with
`icacls '<workspace-local dependency directory>' /reset /T /Q`, then verify a
real import and rerun the combined suite under that same account. Keep this
repair scoped to the affected local dependencies.

For a short development loop, select the affected checks or QGIS test file with
`-Checks` and `-QgisPattern` as above; use the complete `-Package` run for final
verification. Integration logs include the ten slowest test cases on Python
3.12+, including setup and cleanup, to help identify expensive scenarios.
Older Python versions retain the same checks without duration reporting.
For direct `unittest` commands on Python 3.12+, append `--durations 10` to obtain
the same report ([Python documentation](https://docs.python.org/3.12/library/unittest.html#command-line-options)).

## Shared QGIS test environment

### Workspace runtime setup

To prepare either baseline without a machine-wide QGIS installation, run:

```powershell
./scripts/setup-qgis-runtime.ps1 -Version 3.44.0
./scripts/setup-qgis-runtime.ps1 -Version 4.2.3
./scripts/setup-qgis-runtime.ps1 -List
```

[setup-qgis-runtime.ps1](../../scripts/setup-qgis-runtime.ps1) uses Windows
CPython **3.10–3.12** and an existing **7-Zip** installation. The wrapper selects
Python from PATH, falling back to a QGIS installation's bundled executable.
Supply `-Python 'C:\path\to\python.exe'` or `-SevenZip 'C:\path\to\7z.exe'`
when needed. Python 3.13+ removed the `_msi` module used to read MSI tables;
an existing QGIS `apps/Python312/python.exe` works without its batch launcher.
The equivalent Python entry point is `python scripts/setup_qgis_runtime.py --help`.
Omitting `-Version` selects the manifest's default baseline, currently 4.2.3.

Local setup and CI read the same [runtime manifest](../../scripts/qgis-runtimes.json).
It owns versions, installer revisions, launcher names and SHA-256 pins. When
updating a pin, obtain its checksum from the installer's official sibling
`.sha256sum` file and verify the resulting runtime before adopting the change.
Downloads can exceed 1 GB; allow several GB of free space for extraction.

All setup artifacts remain in ignored `.local/qgis-runtimes/`. Verified downloads
are cached by SHA-256 and rechecked on every run. To reuse an already downloaded
MSI, add `-Installer 'C:\path\to\QGIS-OSGeo4W-3.44.0-1.msi'`; the file is copied
into the cache and checked against the selected pin. A partial or mismatched
download is never promoted to a cache hit. Setup reads MSI tables and extracts
files with 7-Zip; it does not run installer actions, change machine installations,
install Python dependencies or open QGIS user profiles.

Setup validates the shipped Python launcher by importing QGIS and checking its
exact pinned version, then prints its absolute path, a check-runner command and
an optional session-only `QGIS_PYTHON` assignment. Use that output with
`./scripts/check.ps1 -QgisPython '…'`; the launcher's basename comes from the
selected installer. Repeated setup validates and reuses the completed extraction
without network access. A failed setup exits nonzero with diagnostics; extraction
and version-check logs stay in its local stage. `-Rebuild` creates a fresh stage
while preserving earlier extractions. A checksum mismatch requires removing the
reported invalid cache file before retrying. Failed/rebuilt stages are retained
for inspection and may be removed manually when no longer needed.

### Baseline checks

Run source and packaged checks on both **QGIS 3.44.0 (Qt 5)** and
**QGIS 4.2.3 (Qt 6)**. The default launcher remains 4.2.3; select the other
installation explicitly, for example:

```powershell
./scripts/check.ps1 -Package -QgisPython 'C:\Program Files\QGIS 3.44.0\bin\python-qgis.bat'
./scripts/check.ps1 -Package
```

Use the launcher actually shipped by the selected installer; LTR-branded packages
may name it `python-qgis-ltr.bat`. Keep separate processes and isolated settings
for each runtime. CI pins both baseline installers and verifies their checksums
and runtime versions.

`RESPONSIBLE_FOREST_PLANNING_TEST_PLUGIN_ROOT` is the sole plugin-root override
for pure and integration tests. When unset, tests use this checkout; the package
check runner sets it to the extracted ZIP. Earlier test-variable aliases are not
supported.

Every integration module calls `qgis_application()` from
[qgis_test_environment.py](../../qgis_plugin/tests/qgis/qgis_test_environment.py)
before importing QGIS or plugin modules. It creates one GUI-capable offscreen
application per process. Temporary INI user/system settings, profile,
authentication storage and provider cache keep test writes and credentials
separate from the user's QGIS profile. File and SQLite write/read probes,
settings persistence/containment, the supported QGIS range and required
provider availability are checked before product tests.

[run_qgis_tests.py](../../scripts/run_qgis_tests.py) supports `--preflight-only`
and `--pattern`, and enables Python fault handling before QGIS initialization,
including direct and CI invocations. Direct unittest uses the same isolation
bootstrap. The runner
allocates a fresh temporary environment for each child and cleans it up after
process exit. Direct runs use best-effort exit cleanup.
`RESPONSIBLE_FOREST_PLANNING_TEST_ENV_ROOT` is available for a caller-owned
temporary directory when using the bootstrap directly.

## Python linting

[Pylint configuration](../../pyproject.toml) covers the plugin, regression tests
and development scripts. Install the pinned
[development dependencies](../../requirements-dev.txt) into the QGIS Python
environment's user site, then run from the repository root:

```powershell
& 'C:\Program Files\QGIS 4.2.3\bin\python-qgis.bat' -m pip install --user --upgrade -r requirements-dev.txt
& 'C:\Program Files\QGIS 4.2.3\bin\python-qgis.bat' -m pylint qgis_plugin scripts
```

Install the current pins in each baseline runtime before linting. They include
Astroid's fix for an infinite loop when inspecting live Qt 5 classes; older
development-tool installations can stall on the QGIS 3.44 bindings.
[Upstream fix](https://github.com/pylint-dev/astroid/releases/tag/v4.3.4).

Use the QGIS launcher so PyQGIS and Qt imports resolve. The repository
configuration enables fatal/error diagnostics and selected correctness warnings;
any enabled diagnostic fails the command. It covers plugin code, tests and
scripts; development dependencies remain outside the installation ZIP. For a
focused check, replace `qgis_plugin scripts` with a file path. Editors and CI
must use the same runtime and repository working directory.

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

Run tooling checks separately from plugin tests with Python 3.10+, the pinned
development dependencies and Git available on PATH:

```powershell
python -m pip install -r requirements-dev.txt
python scripts/check.py --checks tooling
```

The tooling suite includes offline [repository consistency checks](../../scripts/check_consistency.py)
for local Markdown links/anchors (including README images and HTML destinations),
the documented QGIS minimum, metadata/CI matrix agreement, required-check names and release dependencies and
serialization. Exact provider-cache paths in the reference manifest may be absent.
Run just these checks with `python scripts/check_consistency.py`; they also run
with `-Checks tooling` and in CI's required build job. The existing help/package
tests cover installed manuals and preservation of source metadata in the ZIP.

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

The integration suite uses generated local data and loopback WFS/OAPIF/WMTS
fixtures with real QGIS providers. It checks the shared Processing workflow,
GeoPackage/workbook outputs and Finnish/English failures without online services.
Loopback network access is required. WFS 2.0 cases cover production connection
construction, paging, successful-empty responses and later-page failures;
legacy WFS 1.0 fixture transport does not establish production support.

### Regression seams

| Boundary | Regression entry points |
| --- | --- |
| Pure classification and indicator policy | `qgis_plugin/tests/` |
| Geometry, provenance and source/selection contracts | `test_classification_geometry.py`, `test_workflow_contracts.py`, `test_source_field_workflow.py` |
| Backend polygon filtering, candidate reduction, request-size fallback and changed-AOI caches | `test_analysis_query_filtering.py` |
| Coordinated publication and readable saved outputs | `test_publication_failures.py`, `test_wizard_completion.py` |
| Provider initialization and project-layer lifecycle | `test_wfs_initialization.py`, `test_project_tree.py`, parcel/basemap integration tests |
| Operational isolation and logging | `test_qgis_environment.py`, `test_logging_contract.py` |

Integration entry points are under `qgis_plugin/tests/qgis/`. Tests own the
individual scenarios and assertions; use the linked contracts to identify which
boundary a change affects.

`workflow_fixture.py` owns shared source records and Processing scenarios;
`ui_fixture.py` supplies real Qt widgets behind a small QGIS interface adapter.
These helper modules contain no discoverable tests. Inject failures at provider,
writer, filesystem or UI seams; keep numerical expectations independent of
implementation constants. Headless checks do not establish desktop acceptance.

Use real provider and event-loop boundaries for project setup and worker
changes, and compare reopened artifacts by semantic values with tolerances.
Keep source estimates and per-metric denominators independent. Local fixtures
verify adapter behavior; live MML credentials, provider coverage and desktop
map acceptance require separate checks.

To check an extracted plugin ZIP, set `RESPONSIBLE_FOREST_PLANNING_TEST_PLUGIN_ROOT` to the directory
containing the extracted `savonia_responsible_forest_planning_tool` folder and run
the integration command in a new Python process. The test code remains outside
the distributable plugin. GUI acceptance and live-source smoke checks remain
separate from these deterministic checks.

### Automated regression verification

Use the [check runner](#local-check-runner) for source and packaged checks and
the [regression seams](#regression-seams) to select affected suites. Inspect the
runner output or CI logs for results; a maintained test-history summary is not
required. Automated fixtures do not establish live-provider completeness,
interactive desktop/browser/Excel behavior or newer-QGIS compatibility.

## Check packaging separately

Use the [manual acceptance guide](../testing/manual-acceptance.md) for installed
desktop checks, including wizard layout, both languages and expected results.

The linked development checkout is for fast iteration. Use a ZIP install when checking the distributable package:

- Run `./qgis_plugin/package.ps1` in Windows PowerShell from the repository root to build or refresh the ZIP using the version already in `metadata.txt`. This is the ordinary installation and development packaging command; it preserves the metadata version and replaces the ZIP for that version.
- The script includes the source package and copies both repository manuals from `docs/help/` into the installed package's `docs/help/`, adjusting local resource links. Keep the full checkout when building.
- **Release maintainers:** `./qgis_plugin/package.ps1 -BumpMinor` increments the minor version in `metadata.txt`, resets the patch to zero and writes a ZIP. Use the switch only when intentionally preparing a new version; it edits metadata before building, so an archive failure can leave the increment in place. Packaging errors stop the command and remove an incomplete ZIP.
- In QGIS Plugin Manager, use **Install from ZIP** and select the generated file under `qgis_plugin\dist`. For a clean acceptance check, use a separate profile so a previously installed copy cannot be confused with the development source.

After installation, select the appropriate [manual test scope](../testing/manual-acceptance.md#choose-the-scope)
and work through the checklist with that ZIP/runtime.

### Result field organization checks

The result form groups and table columns follow the
[per-polygon field reference](output-schema.md#per-polygon-fields). Regression
checks verify field/value alignment, source-first Finnish/English labels,
persisted GeoPackage form groups and area explanations, and the matching
workbook/documentation order. These checks are part of the
[integration suite](../../qgis_plugin/tests/qgis/test_result_field_organization.py).
Build the ZIP with `./qgis_plugin/package.ps1`, extract it and run the suites
against that copy using `RESPONSIBLE_FOREST_PLANNING_TEST_PLUGIN_ROOT` as described above.

For desktop QGIS/Excel procedures, use
[map review and saved results](../testing/manual-acceptance.md#map-review-and-saved-results).

<a id="grid-indicator-manual-gui-acceptance--pending"></a>

### Grid-indicator manual GUI acceptance

The reusable procedure is now consolidated in the
[manual acceptance guide](../testing/manual-acceptance.md), especially
[inputs/execution](../testing/manual-acceptance.md#inputs-and-execution) and
[numerical interpretation](../testing/manual-acceptance.md#numerical-interpretation-and-exceptional-evidence).
This heading retains existing links. The
[register](../open-questions.md#interactive-acceptance) owns current status.

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

Hosted CI has three required job names: `Test and build installable ZIP`,
`Pylint and QGIS 3.44.0 integration` and `Pylint and QGIS 4.2.3 integration`.
The build supplies the tested installation ZIP; each QGIS job runs lint and
offscreen integration against source and that ZIP. All three must pass before
a main release starts. Workflow failure artifacts
provide diagnostics; exact installation/tooling configuration lives in the
[workflow](../../.github/workflows/build-and-release.yml).

Continue Finnish/English desktop acceptance using the
[manual guide](../testing/manual-acceptance.md).
Offscreen CI does not establish interactive acceptance or compatibility with
newer QGIS releases. Inspect [hosted checks](distribution.md#hosted-checks) for CI
results and [open questions](../open-questions.md#acceptance-and-distribution)
for remaining repository-setting work.

### Required merge checks

Workflow jobs run on pull requests, but preventing a merge also requires active
GitHub branch protection or a ruleset for `main`. Require all three exact check names
above and require the branch to be up to date before merging. Keep existing
protection rules. GitHub documents
[required status checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches#require-status-checks-before-merging).

The [main quality ruleset](../../.github/rulesets/main-quality.json) is an
API-ready definition with those three checks and no bypass actors. A checked-in
JSON file does not activate repository settings. After the updated workflow
has run successfully, a repository administrator can create the additional
ruleset from the repository root:

```powershell
gh api --method POST repos/anttikajanus/savonia-responsible-forest-planning-tool/rulesets --input .github/rulesets/main-quality.json
```

Create it once; inspect the existing repository rulesets before applying it
again. If an equivalent ruleset already exists, update that rule through
GitHub settings instead of creating a duplicate. This adds requirements without
replacing existing protection. The [verification register](../open-questions.md#acceptance-and-distribution)
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
suites with both QGIS baseline launchers shown above. The packaging checks
exercise both modes, including the version-incrementing path only in a temporary
copy; they leave working metadata and generated source caches intact.

For extracted-package verification, set `RESPONSIBLE_FOREST_PLANNING_TEST_PLUGIN_ROOT` to the directory
containing the extracted package and run each suite in a new Python process. All
plugin imports in the regression suites honor that root. The packaging-script
tests still exercise the checkout's scripts and source package; the Processing
help tests copy the selected package to a separate temporary ZIP installation.
Keep these distinctions when reporting installed-package coverage.

Interactive locale/lifecycle checks and offline/browser/notices checks are owned
by the [manual acceptance guide](../testing/manual-acceptance.md#installation-lifecycle-and-language)
and its [help section](../testing/manual-acceptance.md#help-offline-use-and-notices).
Automated offscreen widget checks supplement those observations. Keep substantive
defects or unanswered questions in the [register](../open-questions.md#interactive-acceptance).

## Related guidance

- [QGIS implementation, testing, and localization guidance](../agents/qgis.md)
- [Development, logging and bilingual help design](operations.md)
- [Plugin installation and workflow](../../qgis_plugin/README.md)
