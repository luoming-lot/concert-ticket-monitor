@echo off
chcp 65001 >nul
title 演唱会票务监控系统

echo ============================================
echo     🎫 演唱会票务监控系统 - 启动脚本
echo ============================================
echo.

:: 检查 Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.12+
    pause
    exit /b 1
)

:: 检查 Node.js
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [警告] 未找到 Node.js，前端将无法启动
)

echo [1/4] 检查后端依赖...
cd /d "%~dp0backend"

if not exist "venv" (
    echo [信息] 创建 Python 虚拟环境...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo [2/4] 安装 Python 依赖...
pip install -r requirements.txt -q

echo [3/4] 初始化数据库...
python init_db.py

echo [4/4] 启动服务...
echo.
echo 后端 API:  http://localhost:8000
echo API 文档: http://localhost:8000/docs
echo 前端页面: http://localhost:5173
echo.
echo 按 Ctrl+C 停止服务
echo ============================================

start "Concert-Monitor-Frontend" cmd /c "cd /d %~dp0frontend && npm install && npm run dev"
start "Concert-Monitor-Backend" cmd /c "cd /d %~dp0backend && venv\Scripts\python run.py"

echo 服务已启动！请访问 http://localhost:5173
pause
