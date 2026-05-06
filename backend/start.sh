#!/bin/bash
# 粤海物业数字化平台 - 后端启动脚本

echo "=================================="
echo "粤海物业数字化平台 - 后端服务"
echo "=================================="

# 进入后端目录
cd "$(dirname "$0")/.."

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "安装依赖..."
pip install -r requirements.txt

# 启动服务
echo "启动服务..."
python main.py
