# ============================================================================
# Move Docker Desktop Data to D:\AppData\Docker
# ============================================================================
# This script moves Docker's WSL2 data to a new location to free up space
# Run as Administrator in PowerShell

$NewDockerPath = "D:\AppData\Docker"
$BackupPath = "$NewDockerPath\docker-desktop-data.tar"
$BackupPath2 = "$NewDockerPath\docker-desktop.tar"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Docker Data Migration Script" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Create target directory
Write-Host "[1/6] Creating target directory..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $NewDockerPath | Out-Null
Write-Host "✓ Directory created: $NewDockerPath" -ForegroundColor Green
Write-Host ""

# Step 2: Stop Docker Desktop
Write-Host "[2/6] Stopping Docker Desktop..." -ForegroundColor Yellow
Write-Host "Please close Docker Desktop manually if it's running." -ForegroundColor Red
Write-Host "Press Enter when Docker Desktop is closed..." -ForegroundColor Yellow
Read-Host

# Step 3: Shutdown WSL
Write-Host "[3/6] Shutting down WSL..." -ForegroundColor Yellow
wsl --shutdown
Start-Sleep -Seconds 5
Write-Host "✓ WSL shutdown complete" -ForegroundColor Green
Write-Host ""

# Step 4: Export docker-desktop-data
Write-Host "[4/6] Exporting docker-desktop-data (this may take 10-30 minutes)..." -ForegroundColor Yellow
wsl --export docker-desktop-data $BackupPath
if (Test-Path $BackupPath) {
    $size = (Get-Item $BackupPath).Length / 1GB
    Write-Host "✓ Export complete: $([math]::Round($size, 2)) GB" -ForegroundColor Green
} else {
    Write-Host "✗ Export failed!" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 5: Export docker-desktop
Write-Host "[5/6] Exporting docker-desktop..." -ForegroundColor Yellow
wsl --export docker-desktop $BackupPath2
if (Test-Path $BackupPath2) {
    $size = (Get-Item $BackupPath2).Length / 1GB
    Write-Host "✓ Export complete: $([math]::Round($size, 2)) GB" -ForegroundColor Green
} else {
    Write-Host "✗ Export failed!" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 6: Unregister old distributions
Write-Host "[6/6] Unregistering old WSL distributions..." -ForegroundColor Yellow
Write-Host "WARNING: This will delete the old Docker data!" -ForegroundColor Red
Write-Host "Type 'YES' to continue or anything else to cancel:" -ForegroundColor Yellow
$confirmation = Read-Host

if ($confirmation -eq "YES") {
    wsl --unregister docker-desktop-data
    wsl --unregister docker-desktop
    Write-Host "✓ Old distributions removed" -ForegroundColor Green
    Write-Host ""
    
    # Re-import to new location
    Write-Host "Re-importing docker-desktop-data..." -ForegroundColor Yellow
    wsl --import docker-desktop-data "$NewDockerPath\data" $BackupPath --version 2
    
    Write-Host "Re-importing docker-desktop..." -ForegroundColor Yellow
    wsl --import docker-desktop "$NewDockerPath\distro" $BackupPath2 --version 2
    
    Write-Host "✓ Import complete!" -ForegroundColor Green
    Write-Host ""
    
    # Cleanup
    Write-Host "Cleaning up backup files..." -ForegroundColor Yellow
    Remove-Item $BackupPath -Force
    Remove-Item $BackupPath2 -Force
    Write-Host "✓ Cleanup complete" -ForegroundColor Green
    
} else {
    Write-Host "Operation cancelled. Backup files kept at:" -ForegroundColor Yellow
    Write-Host "  - $BackupPath" -ForegroundColor Cyan
    Write-Host "  - $BackupPath2" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Migration Complete!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Start Docker Desktop" -ForegroundColor White
Write-Host "2. Verify everything works: docker ps" -ForegroundColor White
Write-Host "3. Your Docker data is now at: $NewDockerPath" -ForegroundColor White
