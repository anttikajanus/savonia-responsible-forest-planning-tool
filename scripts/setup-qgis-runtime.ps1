param(
    [string]$Version,
    [string]$Python,
    [string]$Installer,
    [string]$SevenZip,
    [switch]$List,
    [switch]$Rebuild
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'development-paths.ps1')
$paths = Get-DevelopmentPaths -Repository (Split-Path $PSScriptRoot -Parent) -Python $Python
$Python = $paths.Python
if (-not $Python) { throw 'Supply -Python with a Windows CPython 3.10-3.12 executable, such as QGIS apps/Python312/python.exe.' }

$arguments = @((Join-Path $PSScriptRoot 'setup_qgis_runtime.py'))
if ($Version) { $arguments += @('--version', $Version) }
if ($Installer) { $arguments += @('--installer', $Installer) }
if ($SevenZip) { $arguments += @('--seven-zip', $SevenZip) }
if ($List) { $arguments += '--list' }
if ($Rebuild) { $arguments += '--rebuild' }
& $Python @arguments
exit $LASTEXITCODE
