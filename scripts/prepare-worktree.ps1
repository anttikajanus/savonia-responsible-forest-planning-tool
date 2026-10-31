param([string]$Name, [string]$Spec, [string]$Base = 'HEAD', [string]$Branch,
      [string]$QgisVersion, [string]$Python, [switch]$Probe)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'development-paths.ps1')
$paths = Get-DevelopmentPaths -Repository (Split-Path $PSScriptRoot -Parent) -Python $Python
if (-not $paths.Python) { throw 'Supply -Python or run setup-dev-environment.ps1 first.' }
$arguments = @((Join-Path $PSScriptRoot 'prepare_worktree.py'))
if ($Probe) { $arguments += '--probe' }
if ($Name) { $arguments += @('--name', $Name) }
if ($Spec) { $arguments += @('--spec', $Spec) }
if ($Branch) { $arguments += @('--branch', $Branch) }
if ($QgisVersion) { $arguments += @('--qgis-version', $QgisVersion) }
$arguments += @('--base', $Base)
& $paths.Python @arguments
exit $LASTEXITCODE
