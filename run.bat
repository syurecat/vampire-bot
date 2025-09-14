@echo off
cd /d %~dp0 || (echo Failed to change directories & pause & exit /b)
if not exist main.py (echo vampire.py not found & pause & exit /b)
py main.py
pause