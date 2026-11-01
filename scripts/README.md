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
| [`prepare_release.py`](prepare_release.py) | Prepare the next release version in the build workflow. | [GitHub builds and releases](../docs/architecture/development.md#automatic-github-builds-and-releases) |

The PowerShell setup and worktree commands are Windows entry points. Python
counterparts and focused direct commands are available where documented in the
development guide.

Other files support these commands and CI. Use the linked development or release
guide when changing their behavior. Automated script tests are in [`tests/`](tests/).
