@echo off
chcp 65001 >nul
echo ============================================
echo     坦克大战 - Windows 安装脚本
echo ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python！
    echo 请先安装 Python 3.8 或更高版本：https://www.python.org/downloads/
    echo 安装时请务必勾选 "Add Python to PATH"
    pause
    exit /b 1
)

echo [1/3] Python 已检测到...
python --version
echo.

REM Create virtual environment (optional but recommended)
echo [2/3] 安装依赖...
pip install -r requirements.txt
if errorlevel 1 (
    echo [错误] 依赖安装失败！
    pause
    exit /b 1
)
echo.

echo [3/3] 启动游戏...
echo ============================================
echo 控制说明：
echo   W/↑ - 向上移动
echo   S/↓ - 向下移动  
echo   A/← - 向左移动
echo   D/→ - 向右移动
echo   空格 - 射击
echo   R    - 重新开始
echo   ESC  - 退出
echo ============================================
echo.
python main.py

pause
