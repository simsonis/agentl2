@echo off
REM AgentL2 LLM Server Starter
REM This script starts the real_agent_server.py

echo ========================================
echo AgentL2 LLM Server Starter
echo ========================================
echo.
echo Starting LLM Server on port 8001...
echo Using: real_agent_server.py
echo.

cd /d %~dp0
python real_agent_server.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Server failed to start!
    echo.
    echo Troubleshooting:
    echo 1. Check OPENAI_API_KEY in .env file
    echo 2. Ensure port 8001 is not in use
    echo 3. Check Python dependencies are installed
    pause
    exit /b 1
)
