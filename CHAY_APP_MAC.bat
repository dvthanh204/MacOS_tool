@echo off
title LockSlide Studio macOS // He Thong Ma Hoa Bai Giang Cho MacBook
cd /d "%~dp0"
python app_mac.py
if errorlevel 1 (
    echo.
    echo [LOI] Khong the khoi dong LockSlide Studio macOS. Vui long kiem tra Python da duoc cai dat.
    pause
)
