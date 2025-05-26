#!/bin/bash

# 法院判例知识库 - 云端查询服务启动脚本
# 适用于1C2G低资源环境

echo "🚀 启动法院判例知识库云端查询服务..."

# 设置环境变量
export FLASK_HOST="0.0.0.0"
export FLASK_PORT="5000"
export FLASK_DEBUG="False"
export CHROMA_DATA_PATH="./db/"

# 检查数据库目录
if [ ! -d "./db" ]; then
    echo "❌ 错误: 数据库目录 ./db 不存在"
    echo "请先上传向量数据库文件到 ./db 目录"
    exit 1
fi

# 检查ChromaDB文件
if [ ! -f "./db/chroma.sqlite3" ]; then
    echo "❌ 错误: ChromaDB数据库文件不存在"
    echo "请先上传 chroma.sqlite3 文件到 ./db 目录"
    exit 1
fi

echo "✅ 数据库文件检查通过"

# 启动服务（使用gunicorn生产环境部署）
echo "🔄 启动 Gunicorn 服务器..."
gunicorn -w 1 -b 0.0.0.0:5000 --timeout 60 --max-requests 1000 app_cloud:app

# 如果需要调试，可以使用Flask开发服务器：
# python app_cloud.py 