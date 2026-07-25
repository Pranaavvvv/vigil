$ErrorActionPreference = "Stop"

$ProjectDir = Get-Location
$OutFile = "$ProjectDir\vigil-submission.zip"

if (Test-Path $OutFile) {
    Remove-Item $OutFile -Force
}

Write-Host "Creating packaging manifest..."
# Create a temporary directory
$TempDir = Join-Path $env:TEMP "vigil_pkg"
if (Test-Path $TempDir) {
    Remove-Item $TempDir -Recurse -Force
}
New-Item -ItemType Directory -Path $TempDir | Out-Null

Write-Host "Copying files to staging directory..."
Copy-Item -Path "api", "data", "data_gen", "detection", "explain", "profiling" -Destination $TempDir -Recurse -PassThru | Out-Null
Copy-Item -Path "frontend" -Destination $TempDir -Recurse -PassThru | Out-Null
Copy-Item -Path "*.md", "*.py", "requirements.txt" -Destination $TempDir -PassThru | Out-Null

Write-Host "Cleaning up excluded directories (node_modules, __pycache__)..."
Get-ChildItem -Path $TempDir -Recurse -Directory -Filter "node_modules" | Remove-Item -Recurse -Force
Get-ChildItem -Path $TempDir -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -Path $TempDir -Recurse -Directory -Filter ".git" | Remove-Item -Recurse -Force

Write-Host "Compressing archive to $OutFile..."
Compress-Archive -Path "$TempDir\*" -DestinationPath $OutFile -Force

Write-Host "Cleaning up staging directory..."
Remove-Item $TempDir -Recurse -Force

Write-Host "Packaging complete! Deliverable located at: $OutFile"
