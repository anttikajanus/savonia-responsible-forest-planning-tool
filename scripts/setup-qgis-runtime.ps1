param(
    [string]$Version,
    [string]$Python,
    [string]$Installer,
    [string]$SevenZip,
    [switch]$List,
    [switch]$Rebuild
)

$ErrorActionPreference = 'Stop'
if (-not $Python) {
    $command = Get-Command python -CommandType Application -ErrorAction SilentlyContinue
    if ($command -and $command.Source -notmatch '\\Microsoft\\WindowsApps\\') {
        $Python = $command.Source
    } else {
        $bundled = Get-ChildItem -Path "$env:ProgramFiles/QGIS */apps/Python*/python.exe" -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending | Select-Object -First 1
        if ($bundled) { $Python = $bundled.FullName }
    }
}
if (-not $Python) { throw 'Supply -Python with a Windows CPython 3.10-3.12 executable, such as QGIS apps/Python312/python.exe.' }

$arguments = @((Join-Path $PSScriptRoot 'setup_qgis_runtime.py'))
if ($Version) { $arguments += @('--version', $Version) }
if ($Installer) { $arguments += @('--installer', $Installer) }
if ($SevenZip) { $arguments += @('--seven-zip', $SevenZip) }
if ($List) { $arguments += '--list' }
if ($Rebuild) { $arguments += '--rebuild' }
& $Python @arguments
exit $LASTEXITCODE
