@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Pushing to GitHub...
git push origin master
if %errorlevel% equ 0 (
    echo ✅ Push successful!
) else (
    echo ❌ Push failed
)
pause
