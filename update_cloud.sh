#!/bin/bash

# 法院判例知识库 - 云端服务更新脚本
# 用于在云端服务器快速更新代码和数据库

set -e  # 遇到错误立即退出

echo "🔄 开始更新云端服务..."

# 检查当前分支
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "cloud-deployment" ]; then
    echo "⚠️  当前不在cloud-deployment分支，正在切换..."
    git checkout cloud-deployment
fi

# 拉取最新代码和数据库
echo "📥 拉取最新代码和数据库..."
git pull origin cloud-deployment

# 检查服务状态
SERVICE_RUNNING=$(pgrep -f "app_cloud" || echo "")

if [ -n "$SERVICE_RUNNING" ]; then
    echo "🛑 停止现有服务..."
    pkill -f app_cloud
    sleep 2
    
    # 确保进程完全停止
    if pgrep -f "app_cloud" > /dev/null; then
        echo "⚠️  强制停止服务..."
        pkill -9 -f app_cloud
        sleep 1
    fi
    echo "✅ 服务已停止"
else
    echo "ℹ️  没有运行中的服务"
fi

# 检查依赖是否需要更新
if [ -f "requirements-cloud.txt" ]; then
    echo "📦 检查依赖..."
    pip install -r requirements-cloud.txt --quiet
fi

# 启动服务
echo "🚀 启动服务..."
nohup python app_cloud.py > app.log 2>&1 &

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 3

# 检查服务状态
for i in {1..10}; do
    if curl -s http://localhost:5000/health > /dev/null 2>&1; then
        echo "✅ 服务启动成功！"
        break
    else
        if [ $i -eq 10 ]; then
            echo "❌ 服务启动失败，请检查日志"
            echo "📝 查看日志: tail -f app.log"
            exit 1
        fi
        echo "⏳ 等待服务启动... ($i/10)"
        sleep 2
    fi
done

# 显示服务状态
echo ""
echo "📊 服务状态:"
curl -s http://localhost:5000/health | python -m json.tool 2>/dev/null || echo "无法获取服务状态"

echo ""
echo "✅ 云端服务更新完成！"
echo ""
echo "📋 常用命令:"
echo "   查看日志: tail -f app.log"
echo "   停止服务: pkill -f app_cloud"
echo "   重启服务: pkill -f app_cloud && python app_cloud.py"
echo "   健康检查: curl http://localhost:5000/health" 