@echo off
echo ==========================================
echo    Tax Deduction Finder - Docker Deploy
echo ==========================================
echo.

:: Check if .env file exists
if not exist .env (
    echo ERROR: .env file not found!
    echo.
    echo Please create a .env file with your configuration:
    echo   copy .env.example .env
    echo   Then edit .env and add your GROQ_API_KEY
    pause
    exit /b 1
)

:: Check if GROQ_API_KEY is set
findstr /C:"GROQ_API_KEY=gsk_" .env >nul
if errorlevel 1 (
    echo WARNING: GROQ_API_KEY not configured in .env
    echo Please add your Groq API key to continue
    pause
    exit /b 1
)

echo [OK] Configuration verified
echo.

:: Stop any existing containers
echo [*] Stopping existing containers...
docker compose down -v

echo.
echo [*] Building Docker images (this may take a few minutes)...
docker compose build --no-cache

echo.
echo [*] Starting services...
docker compose up -d

echo.
echo [*] Waiting for services to become healthy...
timeout /t 10 /nobreak >nul

:: Check service status
echo.
echo [*] Service Status:
docker compose ps

echo.
echo ==========================================
echo    Deployment Complete!
echo ==========================================
echo.
echo Access your application:
echo    Backend API:  http://localhost:8000
echo    Frontend UI:  http://localhost:8501
echo    API Docs:     http://localhost:8000/docs
echo.
echo Useful commands:
echo    View logs:     docker compose logs -f
echo    Stop services: docker compose down
echo    Restart:       docker compose restart
echo.
pause
