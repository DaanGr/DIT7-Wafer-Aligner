# FMU Build Script for .NET
# Automates the creation of a valid FMU 2.0 Co-Simulation archive

$ErrorActionPreference = "Stop"

$projectName = "FMU.NET"
$fmuName = "WaferSlipDynamics"
$outputDir = "fmu_build"
$releaseDir = "bin\Release\net48"

Write-Host "--- 1. Cleaning previous builds ---" -ForegroundColor Cyan
if (Test-Path $outputDir) { Remove-Item $outputDir -Recurse -Force }
if (Test-Path "$fmuName.fmu") { Remove-Item "$fmuName.fmu" -Force }

Write-Host "--- 2. Building .NET assembly (Release) ---" -ForegroundColor Cyan
dotnet build -c Release

Write-Host "--- 3. Creating FMU Directory Structure ---" -ForegroundColor Cyan
New-Item -Path "$outputDir" -ItemType Directory | Out-Null
New-Item -Path "$outputDir\binaries\win64" -ItemType Directory -Force | Out-Null
New-Item -Path "$outputDir\resources" -ItemType Directory -Force | Out-Null
New-Item -Path "$outputDir\documentation" -ItemType Directory -Force | Out-Null

Write-Host "--- 4. Copying Files ---" -ForegroundColor Cyan
# Copy XML
Copy-Item "modelDescription.xml" -Destination "$outputDir\modelDescription.xml"

# Copy DLL and dependencies
$dllPath = "$releaseDir\$fmuName.dll"
if (-not (Test-Path $dllPath)) {
    Write-Error "Could not find built DLL at $dllPath"
    exit 1
}
Copy-Item "$releaseDir\*.dll" -Destination "$outputDir\binaries\win64\"

Write-Host "--- 5. Zipping to .fmu ---" -ForegroundColor Cyan
$compressSource = Join-Path (Get-Location) $outputDir
$compressDest = Join-Path (Get-Location) "$fmuName.zip"

Compress-Archive -Path "$compressSource\*" -DestinationPath $compressDest

# Rename .zip to .fmu
Rename-Item "$fmuName.zip" "$fmuName.fmu"

Write-Host "--- SUCCESS ---" -ForegroundColor Green
Write-Host "FMU created at: $(Get-Location)\$fmuName.fmu"
Write-Host "You can now import this file into Siemens NX MCD."