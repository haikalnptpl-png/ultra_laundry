@echo off
title Ultra Laundry System
cd /d "%~dp0"

echo ==========================================
echo   ULTRA LAUNDRY SYSTEM - Menjalankan...
echo ==========================================
echo.

python -m streamlit run app.py

echo.
echo Aplikasi berhenti. Tekan tombol apa saja untuk menutup.
pause >nul
