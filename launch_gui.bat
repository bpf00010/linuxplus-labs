@echo off
rem Launcher script for lplab Native Desktop GUI
cd /d "%~dp0"
if exist "%~dp0lplab.exe" (
    start "" "%~dp0lplab.exe" gui %*
) else if exist "%~dp0dist\lplab.exe" (
    start "" "%~dp0dist\lplab.exe" gui %*
) else if exist "%~dp0.venv\Scripts\pythonw.exe" (
    start "" "%~dp0.venv\Scripts\pythonw.exe" -m lplab.gui %*
) else if exist "%~dp0.venv\Scripts\python.exe" (
    start "" "%~dp0.venv\Scripts\python.exe" -m lplab.gui %*
) else (
    start "" pythonw -m lplab.gui %*
)
