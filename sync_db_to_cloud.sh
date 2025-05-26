#!/bin/bash

# 法院判例知识库 - 数据库同步脚本
# 将主分支的数据库文件同步到云端部署分支

set -e  # 遇到错误立即退出

echo "🔄 开始同步数据库到云端分支..."

# 保存当前分支
CURRENT_BRANCH=$(git branch --show-current)
echo "📌 当前分支: $CURRENT_BRANCH"

# 确保工作目录干净
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  工作目录有未提交的更改，请先提交或储藏"
    git status --short
    exit 1
fi

# 切换到主分支并更新数据库
echo "📂 切换到主分支..."
git checkout main

echo "🔄 重新生成向量数据库..."
python vectorize_and_store.py

echo "💾 提交数据库更改..."
git add db/
if git diff --cached --quiet; then
    echo "ℹ️  数据库无变化，跳过提交"
else
    git commit -m "更新向量数据库 $(date '+%Y-%m-%d %H:%M:%S')"
    echo "📤 推送到远程main分支..."
    git push origin main
fi

# 切换到云端分支并同步数据库
echo "☁️  切换到云端部署分支..."
git checkout cloud-deployment

echo "📋 从主分支复制数据库文件..."
git checkout main -- db/

echo "💾 提交数据库文件到云端分支..."
git add db/
if git diff --cached --quiet; then
    echo "ℹ️  云端分支数据库已是最新，无需更新"
else
    git commit -m "同步数据库文件 $(date '+%Y-%m-%d %H:%M:%S')"
    echo "📤 推送到远程cloud-deployment分支..."
    git push origin cloud-deployment
fi

# 回到原始分支
echo "🔙 回到原始分支: $CURRENT_BRANCH"
git checkout "$CURRENT_BRANCH"

echo "✅ 数据库同步完成！"
echo ""
echo "📊 同步摘要:"
echo "   - 主分支数据库已更新并推送"
echo "   - 云端分支数据库已同步并推送"
echo "   - 当前在分支: $(git branch --show-current)"
echo ""
echo "🚀 下一步: 在云端服务器执行 'git pull origin cloud-deployment' 来更新数据库" 