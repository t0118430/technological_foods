@echo off
REM Quick wrapper for conversation explorer
REM Usage: find_conversation.bat [minutes|hours|session_id]

if "%1"=="" (
    echo Usage: find_conversation.bat [option]
    echo.
    echo Examples:
    echo   find_conversation.bat 30m     - Last 30 minutes
    echo   find_conversation.bat 2h      - Last 2 hours
    echo   find_conversation.bat 1d      - Last 1 day
    echo   find_conversation.bat SESSION_ID - Specific session
    echo.
    goto :eof
)

set INPUT=%1

REM Check if input ends with 'm' (minutes)
echo %INPUT% | findstr /R ".*m$" >nul
if %ERRORLEVEL% EQU 0 (
    set MINUTES=%INPUT:~0,-1%
    python "%~dp0conversation_explorer.py" --minutes-ago %MINUTES% --format detailed
    goto :eof
)

REM Check if input ends with 'h' (hours)
echo %INPUT% | findstr /R ".*h$" >nul
if %ERRORLEVEL% EQU 0 (
    set HOURS=%INPUT:~0,-1%
    python "%~dp0conversation_explorer.py" --hours-ago %HOURS% --format detailed
    goto :eof
)

REM Check if input ends with 'd' (days)
echo %INPUT% | findstr /R ".*d$" >nul
if %ERRORLEVEL% EQU 0 (
    set DAYS=%INPUT:~0,-1%
    python "%~dp0conversation_explorer.py" --days-ago %DAYS% --format detailed
    goto :eof
)

REM Otherwise treat as session ID
python "%~dp0conversation_explorer.py" --session-id %INPUT% --format detailed
