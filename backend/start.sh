#!/bin/bash
# 启动脚本

# 安装依赖
pip install -r requirements.txt

# 初始化数据库
python install_db.py

# 启动服务
python app.py
