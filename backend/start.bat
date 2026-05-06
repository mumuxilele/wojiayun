@echo off
chcp 65001 >nul
echo ==================================
echo 粤海物业数字化平台 - 后端服务
echo ==================================

cd /d "%~dp0.."

:: 检查虚拟环境
if not exist "venv" (
    echo 创建虚拟环境...
    python -m venv venv
)

:: 激活虚拟环境
call venv\Scripts\activate.bat

:: 安装依赖
echo 安装依赖...
pip install -r requirements.txt

:: 启动服务
echo 启动服务...
python main.py

pause