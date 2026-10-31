# Locate a host Python, then let Python own runtime/tooling selection.
function Get-DevelopmentPaths {
    param([string]$Repository, [string]$Python, [string]$QgisPython, [string]$ToolsPath)
    $sharedRoot = $Repository
    $gitCommand = Get-Command git -CommandType Application -ErrorAction SilentlyContinue
    if ($gitCommand) {
        try {
            $worktrees = & $gitCommand.Source -C $Repository worktree list --porcelain 2>$null
            if ($LASTEXITCODE -eq 0 -and $worktrees -and $worktrees[0] -like 'worktree *') { $sharedRoot = $worktrees[0].Substring(9) }
        } catch { Write-Verbose 'Git discovery unavailable; using the supplied checkout.' }
    }
    $hostPython = $Python
    if (-not $hostPython) {
        $managedRoot = Join-Path $sharedRoot '.local/dev-environment'
        $configPath = Join-Path $managedRoot 'environment.json'
        if (Test-Path -LiteralPath $configPath) {
            try {
                $config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
                $contained = [System.IO.Path]::GetFullPath($managedRoot) + [System.IO.Path]::DirectorySeparatorChar
                if ($config.tooling_ready -and $config.python -and ([System.IO.Path]::GetFullPath($config.python)).StartsWith($contained, [System.StringComparison]::OrdinalIgnoreCase) -and (Test-Path -LiteralPath $config.python -PathType Leaf)) { $hostPython = $config.python }
            } catch { Write-Verbose "Managed Python unavailable: $configPath" }
        }
    }
    if (-not $hostPython) {
        foreach ($name in @('python', 'python3')) {
            $command = Get-Command $name -CommandType Application -ErrorAction SilentlyContinue
            if ($command -and $command.Source -notmatch '\\Microsoft\\WindowsApps\\') { $hostPython = $command.Source; break }
        }
    }
    if (-not $hostPython) {
        $launchers = @($QgisPython, $env:QGIS_PYTHON) | Where-Object { $_ }
        $states = Get-ChildItem -Path (Join-Path $sharedRoot '.local/qgis-runtimes/runtimes/*/runtime.json') -ErrorAction SilentlyContinue
        foreach ($stateFile in $states) {
            try {
                $state = Get-Content -LiteralPath $stateFile.FullName -Raw | ConvertFrom-Json
                $candidate = [System.IO.Path]::GetFullPath((Join-Path $stateFile.DirectoryName $state.launcher))
                $contained = [System.IO.Path]::GetFullPath($stateFile.DirectoryName) + [System.IO.Path]::DirectorySeparatorChar
                if ($candidate.StartsWith($contained, [System.StringComparison]::OrdinalIgnoreCase)) { $launchers += $candidate }
            } catch { Write-Verbose "Cached bootstrap Python unavailable: $stateFile" }
        }
        foreach ($launcher in $launchers) {
            $apps = Join-Path (Split-Path (Split-Path $launcher -Parent) -Parent) 'apps'
            $bundled = Get-ChildItem -Path (Join-Path $apps 'Python*/python.exe') -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | Select-Object -First 1
            if ($bundled) { $hostPython = $bundled.FullName; break }
        }
        if (-not $hostPython) {
            $bundled = Get-ChildItem -Path "$env:ProgramFiles/QGIS */apps/Python*/python.exe" -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | Select-Object -First 1
            if ($bundled) { $hostPython = $bundled.FullName }
        }
    }
    if ($hostPython) {
        $arguments = @((Join-Path $Repository 'scripts/dev_environment.py'), '--repository', $Repository)
        if ($Python) { $arguments += @('--python', $Python) }
        if ($QgisPython) { $arguments += @('--qgis-python', $QgisPython) }
        if ($ToolsPath) { $arguments += @('--tools-path', $ToolsPath) }
        try {
            $resolved = & $hostPython @arguments 2>$null
            if ($LASTEXITCODE -eq 0) {
                $paths = $resolved | ConvertFrom-Json
                return [PSCustomObject]@{Python=$paths.python; QgisPython=$paths.qgis_python; ToolsPath=$paths.tools_path; SharedRoot=$paths.shared_root}
            }
        } catch { Write-Verbose 'Path discovery failed; the check runner will report its prerequisite failure.' }
    }
    [PSCustomObject]@{Python=$hostPython; QgisPython=$QgisPython; ToolsPath=$ToolsPath; SharedRoot=$sharedRoot}
}
