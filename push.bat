@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 📤 推送到 GitHub...
git push origin master
if %errorlevel% equ 0 (
    echo ✅ 推送成功! https://github.com/luoming-lot/concert-ticket-monitor
) else (
    echo ❌ 推送失败，请检查网络
)
pause
