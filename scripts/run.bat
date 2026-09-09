@echo off
title Antigravity Perpetual Supervisor
echo ========================================================================
echo  [+] LAUNCHING ANTIGRAVITY PERPETUAL SUPERVISOR
echo ========================================================================

where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [-] Python 3 is required but was not found in your PATH.
    echo     Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

python -m antigravity_perpetual run
if %ERRORLEVEL% neq 0 (
    echo.
    echo [-] Perpetual supervisor exited with code %ERRORLEVEL%.
    pause
)
