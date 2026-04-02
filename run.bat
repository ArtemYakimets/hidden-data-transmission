@echo off
:: run.bat — Start all VMs for the covert channel lab stand.
:: After VMs are up, use run_lab1.bat or run_lab3.bat to run demos.

echo === Starting VMs ===
vagrant up
if errorlevel 1 (
    echo [!] Failed to start VMs
    exit /b 1
)
echo.
echo VMs ready. Next steps:
echo   run_lab1.bat           — Lab 1: passive security device
echo   run_lab3.bat           — Lab 3: active countermeasures
