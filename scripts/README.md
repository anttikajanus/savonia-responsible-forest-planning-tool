# Repository scripts

This directory contains reusable development, verification, reference-cache and
release scripts. Use this page to find the right entry point; the linked guides
own command options and workflow details. Disposable scripts and generated
artifacts belong in ignored `.local/`, as described in the [local artifact
guidance](../docs/agents/issue-tracker.md#local-development-artifacts).

## Commands for maintainers

| Script | Purpose | Instructions |
| --- | --- | --- |
| [`check.ps1`](check.ps1) / [`check.py`](check.py) | Run the selected tooling, unit, lint and QGIS checks; optionally validate the packaged plugin. | [Local check runner](../docs/architecture/development.md#local-check-runner) |
| [`setup-dev-environment.ps1`](setup-dev-environment.ps1) | Prepare shared development dependencies and the pinned QGIS test runtimes. | [Development bootstrap](../docs/architecture/development.md#development-bootstrap) |
| [`setup-qgis-runtime.ps1`](setup-qgis-runtime.ps1) | List, install or rebuild a pinned QGIS test runtime. | [QGIS runtime setup](../docs/architecture/development.md#workspace-runtime-setup) |
| [`prepare-worktree.ps1`](prepare-worktree.ps1) | Prepare an isolated ticket worktree and its task context. | [Prepared ticket worktrees](../docs/architecture/development.md#prepared-ticket-worktrees) |
| [`download_references.py`](download_references.py) | Populate the ignored cache of provider capabilities, schemas and documents. | [Service metadata](../docs/references/service-metadata/README.md) |
| [`check_consistency.py`](check_consistency.py) | Run offline checks for documentation links and distribution configuration. | [Tooling checks](../docs/architecture/development.md#python-linting) |
| [`prepare_release.py`](prepare_release.py) | Prepare the next release version in the build workflow. | [GitHub builds and releases](../docs/architecture/distribution.md#github-builds-and-releases) |

The PowerShell setup and worktree commands are Windows entry points. Python
counterparts and focused direct commands are available where documented in the
development guide.

## Supporting scripts

These are implementation details of the commands above or of CI; normally use
their owning command or workflow instead.

| Script | Used by |
| --- | --- |
| `development-paths.ps1`, `dev_environment.py` | Resolve shared Python, QGIS and tooling paths across linked worktrees. |
| `setup_dev_environment.py`, `setup_qgis_runtime.py`, `qgis-runtimes.json` | Bootstrap tools and runtimes from the PowerShell setup commands and CI. |
| `development_sitecustomize.py` | Load bundled Python DLL paths in the managed development environment. |
| `check_tooling_environment.py`, `check_lint_environment.py` | Preflight parser and lint dependencies for the check runner. |
| `run_dev_tool.py` | Run lint tools with the managed dependencies inside QGIS Python. |
| `run_qgis_tests.py` | Run isolated PyQGIS checks from the check runner and CI. |
| `check_report.py` | Write check-run summaries and stage records. |

Automated tests for these scripts are in [`tests/`](tests/).
