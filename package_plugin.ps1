# Package QGIS Plugin for Distribution
# This script creates a properly formatted ZIP file for QGIS plugin repository

$PluginName = "custom_map_downloader"

# Read version from metadata.txt
$MetadataPath = Join-Path $PSScriptRoot "metadata.txt"
$Version = "0.1.0"  # Default fallback

if (Test-Path $MetadataPath) {
    $MetadataContent = Get-Content $MetadataPath
    foreach ($line in $MetadataContent) {
        if ($line -match '^version=(.+)$') {
            $Version = $matches[1].Trim()
            break
        }
    }
}

$ZipFileName = "$PluginName-$Version.zip"

# Get paths
$PluginDir = $PSScriptRoot
$ParentDir = Split-Path $PluginDir -Parent
$ZipPath = Join-Path $ParentDir $ZipFileName

Write-Host "Creating plugin package: $ZipFileName" -ForegroundColor Green
Write-Host "Plugin directory: $PluginDir"
Write-Host "Output path: $ZipPath"
Write-Host ""

# Remove old ZIP if exists
if (Test-Path $ZipPath) {
    Write-Host "Removing existing ZIP: $ZipPath" -ForegroundColor Yellow
    Remove-Item $ZipPath -Force
}

# Files and patterns to exclude
$ExcludePatterns = @(
    '.git',
    '.gitignore',
    '__pycache__',
    '*.pyc',
    '*.pyo',
    '*.qm',
    '.vscode',
    '.idea',
    '*.swp',
    '*.swo',
    '*.zip',
    'build',
    'dist',
    '.DS_Store',
    'Thumbs.db',
    '*.tmp',
    '*.bak',
    '*~',
    '*.md',
    'package_plugin.py',
    'package_plugin.ps1',
    'plugin_upload.py',
    '*.bat',
    '*.sh',
    'help',
    'scripts',
    'test'
)

# Create temporary directory for packaging
$TempDir = Join-Path $env:TEMP "qgis_plugin_temp"
$TempPluginDir = Join-Path $TempDir $PluginName

if (Test-Path $TempDir) {
    Remove-Item $TempDir -Recurse -Force
}
New-Item -ItemType Directory -Path $TempPluginDir -Force | Out-Null

Write-Host "Copying files..." -ForegroundColor Cyan

# Copy all files except excluded ones
$FileCount = 0
$ExcludedCount = 0

Get-ChildItem -Path $PluginDir -Recurse -File | ForEach-Object {
    $RelativePath = $_.FullName.Substring($PluginDir.Length + 1)
    $ShouldExclude = $false
    
    # Check if any part of the path matches exclude patterns
    $PathParts = $RelativePath -split '\\'
    
    foreach ($Pattern in $ExcludePatterns) {
        # Check filename
        if ($_.Name -like $Pattern) {
            $ShouldExclude = $true
            break
        }
        # Check full path
        if ($RelativePath -like "*$Pattern*") {
            $ShouldExclude = $true
            break
        }
        # Check each path component
        foreach ($Part in $PathParts) {
            if ($Part -like $Pattern) {
                $ShouldExclude = $true
                break
            }
        }
        if ($ShouldExclude) { break }
    }
    
    # Special case: include README.md
    if ($_.Name -eq "README.md") {
        $ShouldExclude = $false
    }
    
    if (-not $ShouldExclude) {
        $DestPath = Join-Path $TempPluginDir $RelativePath
        $DestDir = Split-Path $DestPath -Parent
        
        if (-not (Test-Path $DestDir)) {
            New-Item -ItemType Directory -Path $DestDir -Force | Out-Null
        }
        
        Copy-Item $_.FullName -Destination $DestPath -Force
        Write-Host "  Added: $RelativePath" -ForegroundColor Gray
        $FileCount++
    } else {
        Write-Host "  Excluded: $RelativePath" -ForegroundColor DarkGray
        $ExcludedCount++
    }
}

Write-Host ""
Write-Host "Creating ZIP archive..." -ForegroundColor Cyan

# Create ZIP from temp directory
Compress-Archive -Path $TempPluginDir -DestinationPath $ZipPath -Force

# Clean up temp directory
Remove-Item $TempDir -Recurse -Force

Write-Host ""
Write-Host "✓ Package created successfully!" -ForegroundColor Green
Write-Host "  Files included: $FileCount" -ForegroundColor White
Write-Host "  Files excluded: $ExcludedCount" -ForegroundColor White
Write-Host "  Output: $ZipPath" -ForegroundColor White
Write-Host ""
Write-Host "The ZIP file is ready for upload to QGIS Plugin Repository." -ForegroundColor Yellow
Write-Host "Top-level directory name: $PluginName (PEP 8 compliant)" -ForegroundColor Yellow
