@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git commit -m "Update deploy scripts and README"
git push origin master
echo ✅ 已推送到 GitHub
pause
