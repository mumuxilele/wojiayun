#!/bin/bash
# AI Chat 服务部署脚本
# 在阿里云服务器上执行此脚本

echo "========================================="
echo "开始部署 AI Chat 服务"
echo "========================================="

# 进入项目目录
cd /www/wwwroot/wojiayun

# 拉取最新代码
echo ">>> 拉取最新代码..."
git pull origin master

# 进入 aichat 目录
cd aichat

# 安装依赖
echo ">>> 安装 Node 依赖..."
npm install

# 停止旧服务
echo ">>> 停止旧服务..."
pkill -f "node server.js" 2>/dev/null || true

# 启动新服务
echo ">>> 启动 AI Chat 服务..."
nohup node server.js > /tmp/aichat.log 2>&1 &

# 等待服务启动
sleep 2

# 检查服务状态
if pgrep -f "node server.js" > /dev/null; then
    echo "✅ AI Chat 服务启动成功！"
    echo "📍 服务地址: http://47.98.238.209:22314"
    echo "📍 聊天页面: http://47.98.238.209:22314/?access_token=YOUR_TOKEN"
    echo "📍 健康检查: http://47.98.238.209:22314/health"
    echo "📝 日志文件: /tmp/aichat.log"
else
    echo "❌ 服务启动失败，请查看日志: /tmp/aichat.log"
fi

echo "========================================="
