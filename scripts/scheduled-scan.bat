@echo off
REM CrashLens Scheduled Policy Scan - Windows Version
REM Task Scheduler-compatible script for automated policy enforcement

setlocal enabledelayedexpansion

REM Configuration (customize these variables)
set "LOG_DIR=%LOG_DIR%"
if "%LOG_DIR%"=="" set "LOG_DIR=C:\app\logs"

set "POLICY_FILE=%POLICY_FILE%"
if "%POLICY_FILE%"=="" set "POLICY_FILE=C:\app\config\policy.yaml"

set "SLACK_WEBHOOK=%SLACK_WEBHOOK%"

set "OUTPUT_DIR=%OUTPUT_DIR%"
if "%OUTPUT_DIR%"=="" set "OUTPUT_DIR=C:\temp\crashlens-reports"

set "DAYS_TO_SCAN=%DAYS_TO_SCAN%"
if "%DAYS_TO_SCAN%"=="" set "DAYS_TO_SCAN=1"

REM Create output directory
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

REM Generate timestamp for reports
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "TIMESTAMP=%dt:~0,8%_%dt:~8,6%"
set "REPORT_FILE=%OUTPUT_DIR%\crashlens_scan_%TIMESTAMP%.md"

echo 🔍 Starting CrashLens scheduled scan...
echo 📁 Log directory: %LOG_DIR%
echo 📋 Policy file: %POLICY_FILE%
echo 📊 Report file: %REPORT_FILE%

REM Find log files (Windows doesn't have find like Unix, so we'll use a simple approach)
set "LOG_FILES="
for /r "%LOG_DIR%" %%f in (*.jsonl) do (
    set "LOG_FILES=!LOG_FILES! "%%f""
)

if "%LOG_FILES%"=="" (
    echo ⚠️  No log files found in %LOG_DIR%
    exit /b 0
)

echo 📄 Found log files to scan

REM Run CrashLens scan
set "SCAN_COMMAND=crashlens scan"

REM Add policy file if exists
if exist "%POLICY_FILE%" (
    set "SCAN_COMMAND=!SCAN_COMMAND! --policy "%POLICY_FILE%""
)

REM Add Slack webhook if configured
if not "%SLACK_WEBHOOK%"=="" (
    set "SCAN_COMMAND=!SCAN_COMMAND! --slack-webhook "%SLACK_WEBHOOK%""
)

REM Add output format
set "SCAN_COMMAND=!SCAN_COMMAND! --format markdown --fail-on-policy"

REM Process each log file
set "EXIT_CODE=0"
set "TOTAL_VIOLATIONS=0"

for %%f in (%LOG_FILES%) do (
    echo 🔄 Scanning: %%f
    
    !SCAN_COMMAND! %%f > "%REPORT_FILE%.tmp" 2>&1
    if !errorlevel! equ 0 (
        echo ✅ %%f: PASSED
    ) else (
        echo ❌ %%f: VIOLATIONS FOUND  
        set "EXIT_CODE=1"
        REM Count violations (rough estimate)
        findstr /c:"FAIL" /c:"WARN" "%REPORT_FILE%.tmp" > nul 2>&1
        if !errorlevel! equ 0 set /a "TOTAL_VIOLATIONS+=1"
    )
    
    REM Append to main report
    echo ## Scan Results for %%f >> "%REPORT_FILE%"
    echo **Scan Time:** %date% %time% >> "%REPORT_FILE%"
    echo. >> "%REPORT_FILE%"
    type "%REPORT_FILE%.tmp" >> "%REPORT_FILE%" 2>nul
    echo. >> "%REPORT_FILE%"
    echo --- >> "%REPORT_FILE%"
    echo. >> "%REPORT_FILE%"
    
    del "%REPORT_FILE%.tmp" 2>nul
)

REM Generate summary
echo ## 📊 Scan Summary >> "%REPORT_FILE%"
echo - **Files Scanned:** Multiple >> "%REPORT_FILE%"
echo - **Total Violations:** %TOTAL_VIOLATIONS% >> "%REPORT_FILE%"
echo - **Scan Date:** %date% %time% >> "%REPORT_FILE%"
echo - **Exit Code:** %EXIT_CODE% >> "%REPORT_FILE%"

echo 📊 Scan complete!
echo 📄 Report saved to: %REPORT_FILE%
echo 🔢 Total violations: %TOTAL_VIOLATIONS%
echo 🚪 Exit code: %EXIT_CODE%

REM Cleanup old reports (keep last 30 days) - simplified version
forfiles /p "%OUTPUT_DIR%" /m "crashlens_scan_*.md" /d -30 /c "cmd /c del @path" 2>nul

exit /b %EXIT_CODE%
