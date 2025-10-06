@echo off
REM AgentL2 Docker Compose Starter
REM This script starts all services using Docker Compose

echo ========================================
echo AgentL2 Docker Services Starter
echo ========================================
echo.
echo Starting services:
echo   - PostgreSQL (port 5432)
echo   - Adminer (port 8080)
echo   - Collector (port 8000)
echo   - LLM Server (port 8001)
echo   - UI Server (port 3000)
echo.

REM Check if Docker is running
docker info >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Docker is not running!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist .env (
    echo WARNING: .env file not found!
    echo Please create .env file with required variables.
    echo See .env.example for reference.
    pause
    exit /b 1
)

echo Starting Docker Compose...
docker-compose up -d

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Failed to start services!
    echo.
    echo Run 'docker-compose logs' to see error details.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Services started successfully!
echo ========================================
echo.
echo Access points:
echo   - UI:      http://localhost:3000
echo   - LLM API: http://localhost:8001
echo   - Adminer: http://localhost:8080
echo   - Metrics: http://localhost:8000/metrics
echo.
echo To view logs:       docker-compose logs -f
echo To stop services:   docker-compose down
echo.
pause
