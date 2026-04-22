# Rebuild and Start Docker Containers
Write-Host "===================================" -ForegroundColor Cyan
Write-Host "Tax Deduction Finder - Docker Rebuild" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan

# Navigate to project directory
cd "C:\Users\khayatimittal\Downloads\tax_deduction_finder-20260418T111013Z-3-001\tax_deduction_finder"

Write-Host "`n[1/4] Stopping old containers..." -ForegroundColor Yellow
wsl bash -c "docker compose down"

Write-Host "`n[2/4] Building backend (this takes 2-3 minutes)..." -ForegroundColor Yellow
wsl bash -c "docker compose build backend --no-cache"

Write-Host "`n[3/4] Starting all containers..." -ForegroundColor Yellow
wsl bash -c "docker compose up -d"

Write-Host "`n[4/4] Waiting for services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host "`n===================================" -ForegroundColor Green
Write-Host "Containers Status:" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Green
wsl bash -c "docker compose ps"

Write-Host "`n===================================" -ForegroundColor Green
Write-Host "Backend Logs (last 20 lines):" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Green
wsl bash -c "docker compose logs backend --tail=20"

Write-Host "`n===================================" -ForegroundColor Cyan
Write-Host "DONE! Services are running:" -ForegroundColor Cyan
Write-Host "  - Frontend: http://localhost:8501" -ForegroundColor Green
Write-Host "  - Backend API: http://localhost:8000" -ForegroundColor Green
Write-Host "  - API Docs: http://localhost:8000/docs" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Cyan
