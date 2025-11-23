@echo off
REM Build the Windows installer for Motherless Downloader

echo ========================================================================
echo   Building Motherless Downloader Windows Installer
echo ========================================================================
echo.

python build_installer.py

if %errorlevel% neq 0 (
    echo.
    echo Build failed!
    pause
    exit /b %errorlevel%
)

echo.
echo Build completed successfully!
pause

