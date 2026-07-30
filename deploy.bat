@echo off
chcp 65001 >nul
cd /d "%~dp0backend"
echo ==========================================
echo    🚀 部署后端到 Vercel
echo ==========================================
echo.
npx vercel --prod --yes
echo.
echo ==========================================
echo    ✅ 部署完成!
echo    后端: https://backend-delta-six-95.vercel.app
echo    文档: https://backend-delta-six-95.vercel.app/docs
echo ==========================================
pause
