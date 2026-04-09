@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

:: run_lab1.bat — Lab 1 demo: passive security device

set "MSG=Hello from covert channel"

echo =============================================
echo === Lab 1: Passive Security Device        ===
echo === Variant 7: Model 2, Example 8         ===
echo =============================================
echo.

:: cleanup
echo [0] Cleaning up ...
vagrant ssh p2 -c "pkill -f receiver.py 2>/dev/null; pkill -f start_daemon 2>/dev/null; rm -f /tmp/receiver.log /tmp/decoded.txt" 2>nul
vagrant ssh uz -c "pkill -f security_device.py 2>/dev/null; pkill -f start_daemon 2>/dev/null; rm -f /tmp/uz.log" 2>nul
timeout /t 2 /nobreak >nul

:: receiver
echo [1/3] Starting receiver on P2 ...
vagrant ssh p2 -c "cd /home/vagrant/scripts && python3 start_daemon.py /tmp/receiver.log receiver.py -o /tmp/decoded.txt"
timeout /t 2 /nobreak >nul

:: security device (passive)
echo [2/3] Starting security device on UZ (passive) ...
vagrant ssh uz -c "cd /home/vagrant/scripts && python3 start_daemon.py /tmp/uz.log security_device.py --mode passive"
timeout /t 2 /nobreak >nul

:: sender
echo [3/3] Sending: "%MSG%" ...
echo.
vagrant ssh p1 -c "cd /home/vagrant/scripts && python3 sender.py -m \"!MSG!\""
echo.

:: results
timeout /t 3 /nobreak >nul
echo ========== Receiver log ==========
vagrant ssh p2 -c "cat /tmp/receiver.log 2>/dev/null"
echo.
echo ========== Decoded ==========
vagrant ssh p2 -c "cat /tmp/decoded.txt 2>/dev/null"
echo.
echo ========== Lab 1 Done ==========

:: cleanup UZ
vagrant ssh uz -c "pkill -f security_device.py 2>/dev/null" 2>nul

endlocal
