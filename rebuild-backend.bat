@echo off
echo ========================================
echo Rebuilding Backend Container
echo ========================================

echo.
echo Step 1: Building backend image...
docker compose build backend

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo Step 2: Stopping and removing old container...
docker compose down backend

echo.
echo Step 3: Starting new backend container...
docker compose up -d backend

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to start container!
    pause
    exit /b 1
)

echo.
echo Step 4: Waiting for container to start...
timeout /t 5 /nobreak > nul

echo.
echo Step 5: Showing logs...
echo ========================================
docker compose logs backend

echo.
echo ========================================
echo Done! Backend is running.
echo ========================================
echo.
echo To view live logs, run: docker compose logs -f backend
echo To check status, run: docker compose ps
echo To test health, run: curl http://localhost:8000/health
echo.
pause
