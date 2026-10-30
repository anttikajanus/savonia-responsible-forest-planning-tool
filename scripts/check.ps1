param(
    [string]$Python,
    [string]$QgisPython = $(if ($env:QGIS_PYTHON) { $env:QGIS_PYTHON } else { 'C:\Program Files\QGIS 4.2.3\bin\python-qgis.bat' }),
    [ValidateSet('tooling', 'unit', 'lint', 'qgis')][string[]]$Checks = @('tooling', 'unit', 'lint', 'qgis'),
    [string]$QgisPattern = 'test*.py',
    [double]$TimeoutSeconds = 600,
    [string]$LogsDir,
    [switch]$Package
)

$ErrorActionPreference = 'Stop'
if (-not $Python) {
    foreach ($candidate in @('python', 'python3')) {
        $command = Get-Command $candidate -CommandType Application -ErrorAction SilentlyContinue
        if ($command -and $command.Source -notmatch '\\Microsoft\\WindowsApps\\') {
            $Python = $command.Source
            break
        }
    }
    if (-not $Python) {
        $apps = Join-Path (Split-Path (Split-Path $QgisPython -Parent) -Parent) 'apps'
        $bundled = Get-ChildItem -Path (Join-Path $apps 'Python*/python.exe') -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | Select-Object -First 1
        if ($bundled) { $Python = $bundled.FullName }
    }
}
if (-not $Python) { throw 'Plain Python 3.10+ was not found. Supply -Python with its executable path.' }

$arguments = @((Join-Path $PSScriptRoot 'check.py'), '--qgis-python', $QgisPython, '--checks') + $Checks
$arguments += @('--qgis-pattern', $QgisPattern)
$arguments += @('--timeout', $TimeoutSeconds.ToString([System.Globalization.CultureInfo]::InvariantCulture))
if ($LogsDir) { $arguments += @('--logs-dir', $LogsDir) }
if ($Package) { $arguments += '--package' }
& $Python @arguments
exit $LASTEXITCODE
