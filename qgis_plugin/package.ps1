param(
    [switch]$BumpMinor
)

$ErrorActionPreference = 'Stop'

function Write-PluginArchive {
    param(
        [Parameter(Mandatory = $true)][string]$PluginFolder,
        [Parameter(Mandatory = $true)][string]$ArchivePath
    )

    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $source = Get-Item -LiteralPath $PluginFolder -ErrorAction Stop
    $sourceRoot = $source.FullName.TrimEnd('\', '/')
    $helpFolder = Join-Path $source.Parent.Parent.FullName 'docs/help'
    $destination = [System.IO.Path]::GetFullPath($ArchivePath)
    New-Item -ItemType Directory -Path ([System.IO.Path]::GetDirectoryName($destination)) -Force | Out-Null
    if (Test-Path -LiteralPath $destination) {
        Remove-Item -LiteralPath $destination -Force -ErrorAction Stop
    }
    $archive = [System.IO.Compression.ZipFile]::Open($destination, [System.IO.Compression.ZipArchiveMode]::Create)
    try {
        foreach ($language in @('fi', 'en')) {
            $manualName = "manual_$language.html"
            $manual = [System.IO.File]::ReadAllText((Join-Path $helpFolder $manualName))
            # Repository links point to the source package; ZIP links stay offline.
            $manual = $manual.Replace('../../qgis_plugin/' + $source.Name + '/', '../../')
            $entry = $archive.CreateEntry($source.Name + '/docs/help/' + $manualName,
                                         [System.IO.Compression.CompressionLevel]::Optimal)
            $writer = [System.IO.StreamWriter]::new($entry.Open(), [System.Text.UTF8Encoding]::new($false))
            try {
                $writer.Write($manual)
            }
            finally {
                $writer.Dispose()
            }
        }
        Get-ChildItem -LiteralPath $sourceRoot -Recurse -File -Force -ErrorAction Stop | ForEach-Object {
            $relative = $_.FullName.Substring($sourceRoot.Length + 1).Replace('\', '/')
            if ($relative -match '(^|/)__pycache__(/|$)' -or $_.Extension -in '.pyc', '.pyo') {
                return
            }
            $entryName = $source.Name + '/' + $relative
            [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
                $archive, $_.FullName, $entryName, [System.IO.Compression.CompressionLevel]::Optimal
            ) | Out-Null
        }
    }
    catch {
        $archive.Dispose()
        Remove-Item -LiteralPath $destination -Force -ErrorAction SilentlyContinue
        throw
    }
    finally {
        $archive.Dispose()
    }
}

$pluginFolder = Join-Path $PSScriptRoot 'savonia_responsible_forest_planning_tool'
$distFolder = Join-Path $PSScriptRoot 'dist'
$metadataPath = Join-Path $pluginFolder 'metadata.txt'

$metadata = Get-Content -LiteralPath $metadataPath -Raw -Encoding UTF8
$versionMatch = [regex]::Match($metadata, '(?m)^version=(\d+)\.(\d+)\.(\d+)\s*$')
if (-not $versionMatch.Success) {
    throw "Could not read a semantic version from $metadataPath"
}

$version = '{0}.{1}.{2}' -f $versionMatch.Groups[1].Value, $versionMatch.Groups[2].Value, $versionMatch.Groups[3].Value
if ($BumpMinor) {
    $major = [int]$versionMatch.Groups[1].Value
    $minor = [int]$versionMatch.Groups[2].Value + 1
    $version = '{0}.{1}.0' -f $major, $minor
    $metadata = $metadata -replace '(?m)^version=\d+\.\d+\.\d+\s*$', "version=$version"
    [System.IO.File]::WriteAllText($metadataPath, $metadata, [System.Text.UTF8Encoding]::new($false))
}

$archivePath = Join-Path $distFolder "savonia_responsible_forest_planning_tool-$version.zip"

Write-PluginArchive -PluginFolder $pluginFolder -ArchivePath $archivePath
Write-Output $archivePath
