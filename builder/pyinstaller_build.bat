@echo off
REM ===== Optional Local Build (PyInstaller) =====
REM Requires: Python 3.10+ with pip, and 'pip install pyinstaller'
REM Usage: double-click this file OR run from cmd.
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%\.."
pip install --upgrade pyinstaller
pyinstaller --noconfirm --clean --windowed --name LongformBuilder ^
  --add-data "app;app" ^
  app\longform_gui.py
echo.
echo Build finished. Check the 'dist\LongformBuilder' folder for LongformBuilder.exe
pause
