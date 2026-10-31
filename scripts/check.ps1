param(
    [string]$Python,
    [string]$QgisPython,
    [string]$ToolsPath,
    [ValidateSet('tooling', 'unit', 'lint', 'qgis')][string[]]$Checks = @('tooling', 'unit', 'lint', 'qgis'),
    [string]$QgisPattern = 'test*.py',
    [double]$TimeoutSeconds = 600,
    [string]$LogsDir,
    [switch]$Package
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'development-paths.ps1')
$paths = Get-DevelopmentPaths -Repository (Split-Path $PSScriptRoot -Parent) -Python $Python -QgisPython $QgisPython -ToolsPath $ToolsPath
$Python = $paths.Python
$QgisPython = $paths.QgisPython
if (-not $Python) { throw 'Plain Python 3.10+ was not found. Supply -Python with its executable path.' }

$arguments = @((Join-Path $PSScriptRoot 'check.py'), '--checks') + $Checks
if ($QgisPython) { $arguments += @('--qgis-python', $QgisPython) }
$arguments += @('--qgis-pattern', $QgisPattern)
$arguments += @('--timeout', $TimeoutSeconds.ToString([System.Globalization.CultureInfo]::InvariantCulture))
if ($LogsDir) { $arguments += @('--logs-dir', $LogsDir) }
if ($paths.ToolsPath) { $arguments += @('--tools-path', $paths.ToolsPath) }
if ($Package) { $arguments += '--package' }
& $Python @arguments
exit $LASTEXITCODE
