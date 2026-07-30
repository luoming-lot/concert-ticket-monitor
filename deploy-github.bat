@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ==========================================
echo    📦 部署前端到 GitHub Pages
echo ==========================================
echo.
echo [1/3] 构建前端（API 指向本地后端）...
cd frontend
set VITE_API_URL=http://localhost:8000/api
call npx vite build
cd ..

echo.
echo [2/3] 复制到 docs 目录...
if exist docs rmdir /s /q docs
xcopy /e /y frontend\dist\* docs\ >nul

echo.
echo [3/3] 提交并推送...
git add docs
git commit -m "Deploy to GitHub Pages"
git push origin master

echo.
echo ==========================================
echo    ✅ 完成!
echo    访问: https://luoming-lot.github.io/concert-ticket-monitor
echo.
echo    ⚠️ 还需在 GitHub 开启 Pages:
echo       Settings ^> Pages ^> Source 选 "Deploy from a branch"
echo       Branch 选 master, 文件夹选 /docs
echo ==========================================
pause
