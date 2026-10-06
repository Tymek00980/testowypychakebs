@echo off
chcp 65001 >nul
title PYCHA KEBS PRO - Serwer
cd /d "%~dp0"
echo ====================================================
echo   PYCHA KEBS PRO 2.0 - Uruchamianie serwera...
echo ====================================================
echo   Strona glowna:         http://127.0.0.1:5000
echo   Panel Administratora:  http://127.0.0.1:5000/admin
echo   Login:                 admin
echo   Haslo:                 admin123
echo ====================================================
python -X utf8 app.py
pause