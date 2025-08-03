@echo off
REM CrashLens Daily Cost Violation Alert Script for Windows
REM This script runs daily to check for policy violations and send Slack alerts

REM Configuration
set PROJECT_DIR=C:\path\to\your\crashlens\project
set LOG_FILE=C:\logs\crashlens-alerts.log
set POLICY_FILE=policy.yaml
set LOGS_DIR=logs

REM Get today's date in YYYY-MM-DD format
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "YY=%dt:~2,2%" & set "YYYY=%dt:~0,4%" & set "MM=%dt:~4,2%" & set "DD=%dt:~6,2%"
set "TODAY=%YYYY%-%MM%-%DD%"

REM Daily log file (adjust path as needed)
set DAILY_LOG=%LOGS_DIR%\%TODAY%.jsonl
set FALLBACK_LOG=%LOGS_DIR%\latest.jsonl

REM Change to project directory
cd /d "%PROJECT_DIR%" || (
    echo %date% %time% ERROR: Failed to change to project directory: %PROJECT_DIR% >> "%LOG_FILE%"
    exit /b 1
)

REM Check if policy file exists
if not exist "%POLICY_FILE%" (
    echo %date% %time% ERROR: Policy file not found: %POLICY_FILE% >> "%LOG_FILE%"
    exit /b 1
)

REM Determine which log file to use
if exist "%DAILY_LOG%" (
    set LOG_TO_SCAN=%DAILY_LOG%
    echo %date% %time% INFO: Using daily log file: %DAILY_LOG% >> "%LOG_FILE%"
) else if exist "%FALLBACK_LOG%" (
    set LOG_TO_SCAN=%FALLBACK_LOG%
    echo %date% %time% INFO: Daily log not found, using fallback: %FALLBACK_LOG% >> "%LOG_FILE%"
) else (
    echo %date% %time% ERROR: No log files found. Checked: %DAILY_LOG%, %FALLBACK_LOG% >> "%LOG_FILE%"
    exit /b 1
)

REM Check if log file has content (simple check for file size > 0)
for %%I in ("%LOG_TO_SCAN%") do if %%~zI==0 (
    echo %date% %time% INFO: Log file is empty, skipping scan: %LOG_TO_SCAN% >> "%LOG_FILE%"
    exit /b 0
)

echo %date% %time% INFO: Starting CrashLens scan with Slack webhook >> "%LOG_FILE%"

REM Run CrashLens with Slack webhook
REM Using summary mode for daily alerts (recommended)
crashlens scan "%LOG_TO_SCAN%" --policy "%POLICY_FILE%" --summary --slack-webhook "%SLACK_WEBHOOK_URL%" >> "%LOG_FILE%" 2>&1

if %errorlevel% equ 0 (
    echo %date% %time% INFO: CrashLens scan completed successfully >> "%LOG_FILE%"
) else (
    echo %date% %time% ERROR: CrashLens scan failed with exit code: %errorlevel% >> "%LOG_FILE%"
    
    REM Optional: Send error notification to Slack using PowerShell
    powershell -Command "try { Invoke-RestMethod -Uri '%SLACK_WEBHOOK_URL%' -Method Post -ContentType 'application/json' -Body '{\"text\":\"❌ CrashLens daily scan failed with exit code %errorlevel%. Check logs for details.\"}' } catch { }" >nul 2>&1
    
    exit /b %errorlevel%
)

echo %date% %time% INFO: Daily alert script completed >> "%LOG_FILE%"
