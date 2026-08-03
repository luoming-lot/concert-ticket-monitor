@echo off
chcp 65001 >nul
echo ==========================================
echo    🎫 演唱会票务监控系统
echo ==========================================
echo.
echo 启动后端服务...
cd /d "%~dp0backend"
if exist venv\Scripts\python.exe (
    set "PYTHON_EXE=venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)
start "Backend-API" cmd /k "cd /d %~dp0backend && %PYTHON_EXE% -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
echo 后端启动中... http://localhost:8000
echo.
timeout /t 3 /nobreak >nul
echo 启动前端服务...
cd /d "%~dp0frontend"
start "Frontend-UI" cmd /k "cd /d %~dp0frontend && npx vite --host 0.0.0.0 --port 5173"
echo 前端启动中... http://localhost:5173
echo.
echo ==========================================
echo   ✅ 系统已启动
echo   前端: http://localhost:5173
echo   后端: http://localhost:8000/docs
echo   默认账号: admin / admin123
echo ==========================================
pause
