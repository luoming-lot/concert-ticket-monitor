@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ==========================================
echo    📦 部署前端到 GitHub Pages
echo ==========================================
echo.
echo [1/2] 构建前端（API 指向本地后端）...
cd frontend
set VITE_API_URL=http://localhost:8000/api
call npx vite build
cd ..

echo.
echo [2/2] 推送到 gh-pages 分支...
call npx gh-pages -d frontend/dist -m "Deploy to GitHub Pages"

echo.
echo ==========================================
echo    ✅ 完成!
echo    访问: https://luoming-lot.github.io/concert-ticket-monitor
echo ==========================================
pause
