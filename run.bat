@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

:: run.bat — Automated launcher for the covert channel lab stand.
:: Usage:
::   run.bat                              sends default message
::   run.bat Hello world                  sends "Hello world"
::   run.bat --raw -f secret.txt          forward raw args to sender.py

:: ── Parse arguments ──
set "SENDER_ARGS="
if "%~1"=="--raw" (
    set "RAW=1"
    shift
) else (
    set "RAW=0"
)

set "ALL_ARGS="
:parse_loop
if "%~1"=="" goto parse_done
if defined ALL_ARGS (
    set "ALL_ARGS=!ALL_ARGS! %~1"
) else (
    set "ALL_ARGS=%~1"
)
shift
goto parse_loop
:parse_done

if "%RAW%"=="1" (
    set "SENDER_ARGS=!ALL_ARGS!"
) else if defined ALL_ARGS (
    set "SENDER_ARGS=-m \"!ALL_ARGS!\""
) else (
    set "SENDER_ARGS=-m \"Hello from covert channel\""
)

echo === Covert Channel Lab Stand ===
echo.

:: ── 1. Ensure VMs are running ──
echo [1/5] Starting VMs (may take a few minutes on first run) ...
vagrant up
if errorlevel 1 (
    echo [!] Failed to start VMs
    exit /b 1
)
echo.

:: ── 2. Kill leftover processes from previous runs ──
echo [2/5] Cleaning up previous runs ...
vagrant ssh p2 -c "pkill -f receiver.py 2>/dev/null; pkill -f start_daemon 2>/dev/null; rm -f /tmp/receiver.log /tmp/decoded.txt" 2>nul
vagrant ssh uz -c "pkill -f security_device.py 2>/dev/null; pkill -f start_daemon 2>/dev/null; rm -f /tmp/uz.log" 2>nul
timeout /t 1 /nobreak >nul

:: ── 3. Start receiver (P2) via daemon helper ──
echo [3/5] Starting receiver on P2 ...
vagrant ssh p2 -c "cd /home/vagrant/scripts && python3 start_daemon.py /tmp/receiver.log receiver.py -o /tmp/decoded.txt"
timeout /t 2 /nobreak >nul

:: ── 4. Start security device (UZ) via daemon helper ──
echo [4/5] Starting security device on UZ ...
vagrant ssh uz -c "cd /home/vagrant/scripts && python3 start_daemon.py /tmp/uz.log security_device.py"
timeout /t 2 /nobreak >nul

:: ── 5. Run sender (P1) — blocks until transmission completes ──
echo [5/5] Sending covert message ...
echo.
vagrant ssh p1 -c "cd /home/vagrant/scripts && python3 sender.py !SENDER_ARGS!"
echo.

:: ── Collect results ──
timeout /t 3 /nobreak >nul
echo ========== Receiver log ==========
vagrant ssh p2 -c "cat /tmp/receiver.log 2>/dev/null"
echo.
echo ========== Decoded message ==========
vagrant ssh p2 -c "cat /tmp/decoded.txt 2>/dev/null"
echo.
echo === Done ===

endlocal
