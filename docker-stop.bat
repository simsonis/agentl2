@echo off
REM AgentL2 Docker Compose Stopper

echo ========================================
echo AgentL2 Docker Services Stopper
echo ========================================
echo.
echo Stopping all services...
echo.

docker-compose down

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Failed to stop services!
    pause
    exit /b 1
)

echo.
echo ========================================
echo All services stopped successfully!
echo ========================================
echo.
pause
