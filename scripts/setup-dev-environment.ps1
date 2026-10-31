param([string]$Python, [string[]]$Version, [string]$SevenZip, [switch]$Status)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'development-paths.ps1')
$paths = Get-DevelopmentPaths -Repository (Split-Path $PSScriptRoot -Parent) -Python $Python
if (-not $paths.Python) { throw 'Supply -Python with Python 3.10-3.12 or a cached QGIS apps/Python312/python.exe.' }
$arguments = @((Join-Path $PSScriptRoot 'setup_dev_environment.py'))
foreach ($item in $Version) { $arguments += @('--version', $item) }
if ($SevenZip) { $arguments += @('--seven-zip', $SevenZip) }
if ($Status) { $arguments += '--status' }
& $paths.Python @arguments
exit $LASTEXITCODE
