@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

:: run_lab3.bat — Lab 3 demo: active security device countermeasures
:: Variant 7: timing covert channel (inter-packet intervals)

set "MSG=Hello from covert channel"

echo =============================================
echo === Lab 3: Active Security Device         ===
echo === Variant 7: Model 2, Example 8         ===
echo =============================================
echo.
echo Original message: "%MSG%"
echo.

:: ── Scheme 1: Jitter ──
echo --- Scheme 1: Jitter (max=60ms) ---
echo     Limits covert channel bandwidth
echo.

vagrant ssh p2 -c "pkill -f receiver.py 2>/dev/null; pkill -f start_daemon 2>/dev/null; rm -f /tmp/receiver.log /tmp/decoded.txt" 2>nul
vagrant ssh uz -c "pkill -f security_device.py 2>/dev/null; pkill -f start_daemon 2>/dev/null; rm -f /tmp/uz.log" 2>nul
timeout /t 2 /nobreak >nul

echo [1/3] Starting receiver ...
vagrant ssh p2 -c "cd /home/vagrant/scripts && python3 start_daemon.py /tmp/receiver.log receiver.py -o /tmp/decoded.txt"
timeout /t 2 /nobreak >nul

echo [2/3] Starting security device (jitter, max=60ms) ...
vagrant ssh uz -c "cd /home/vagrant/scripts && python3 start_daemon.py /tmp/uz.log security_device.py --mode jitter --max-jitter 0.06"
timeout /t 2 /nobreak >nul

echo [3/3] Sending message ...
vagrant ssh p1 -c "cd /home/vagrant/scripts && python3 sender.py -m \"!MSG!\""
echo.

timeout /t 3 /nobreak >nul
vagrant ssh uz -c "pkill -TERM -f security_device.py 2>/dev/null; sleep 1" 2>nul

echo --- Scheme 1: UZ stats ---
vagrant ssh uz -c "cat /tmp/uz.log 2>/dev/null"
echo.
echo --- Scheme 1: Receiver output ---
vagrant ssh p2 -c "cat /tmp/receiver.log 2>/dev/null"
echo.

:: ── Scheme 2: Regulate ──
echo.
echo --- Scheme 2: Regulate (T=100ms) ---
echo     Completely eliminates timing covert channel
echo.

vagrant ssh p2 -c "pkill -f receiver.py 2>/dev/null; pkill -f start_daemon 2>/dev/null; rm -f /tmp/receiver.log /tmp/decoded.txt" 2>nul
vagrant ssh uz -c "pkill -f security_device.py 2>/dev/null; pkill -f start_daemon 2>/dev/null; rm -f /tmp/uz.log" 2>nul
timeout /t 2 /nobreak >nul

echo [1/3] Starting receiver ...
vagrant ssh p2 -c "cd /home/vagrant/scripts && python3 start_daemon.py /tmp/receiver.log receiver.py -o /tmp/decoded.txt"
timeout /t 2 /nobreak >nul

echo [2/3] Starting security device (regulate, T=100ms) ...
vagrant ssh uz -c "cd /home/vagrant/scripts && python3 start_daemon.py /tmp/uz.log security_device.py --mode regulate --fixed-interval 0.10"
timeout /t 2 /nobreak >nul

echo [3/3] Sending message ...
vagrant ssh p1 -c "cd /home/vagrant/scripts && python3 sender.py -m \"!MSG!\""
echo.

timeout /t 3 /nobreak >nul
vagrant ssh uz -c "pkill -TERM -f security_device.py 2>/dev/null; sleep 1" 2>nul

echo --- Scheme 2: UZ stats ---
vagrant ssh uz -c "cat /tmp/uz.log 2>/dev/null"
echo.
echo --- Scheme 2: Receiver output ---
vagrant ssh p2 -c "cat /tmp/receiver.log 2>/dev/null"
echo.

echo =============================================
echo === Lab 3 Complete                        ===
echo =============================================

endlocal
