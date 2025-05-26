# 法院判例知识库 - 云端查询服务部署指南

## 概述

这是一个专为1C2G云服务器优化的**查询专用版本**，不包含embedding功能，仅提供向量数据库查询服务。数据库文件通过Git管理，部署简单快捷。

## 架构特点

- ✅ **轻量级**: 移除了所有embedding模型和依赖
- ✅ **低资源**: 适合1C2G服务器运行
- ✅ **查询专用**: 只提供搜索和LLM分析功能
- ✅ **Git管理**: 数据库文件纳入版本控制，部署更简单
- ✅ **自动同步**: 通过Git pull即可更新数据库

## 部署步骤

### 方案A: 一键部署（推荐）

```bash
# 1. 克隆项目并切换到云端分支
git clone https://github.com/alantany/fayuanpanli.git
cd fayuanpanli
git checkout cloud-deployment

# 2. 安装依赖
pip install -r requirements-cloud.txt

# 3. 设置环境变量（可选LLM分析）
export LLM_API_URL="你的LLM_API地址"
export LLM_API_KEY="你的API密钥"  
export LLM_MODEL_NAME="模型名称"

# 4. 直接启动服务
python app_cloud.py
```

### 方案B: 生产环境部署

```bash
# 使用gunicorn启动服务
gunicorn -w 1 -b 0.0.0.0:5000 --timeout 60 app_cloud:app

# 或者后台运行
nohup gunicorn -w 1 -b 0.0.0.0:5000 --timeout 60 app_cloud:app > app.log 2>&1 &
```

## 数据库更新流程

### 本地更新数据库

当需要添加新案例或更新现有数据时：

```bash
# 1. 在主分支添加新案例文件
git checkout main
# ... 添加新的案例文件到相应目录 ...

# 2. 重新生成向量数据库
python vectorize_and_store.py

# 3. 提交更改
git add .
git commit -m "更新案例数据库"
git push origin main
```

### 同步到云端分支

```bash
# 4. 将数据库文件合并到云端分支
git checkout cloud-deployment

# 5. 从主分支复制数据库文件
git checkout main -- db/
git add db/
git commit -m "同步最新的数据库文件"
git push origin cloud-deployment
```

### 云端更新

```bash
# 在云端服务器执行
git pull origin cloud-deployment

# 重启服务
pkill -f app_cloud
python app_cloud.py
```

## 自动化脚本

### 本地数据库同步脚本

创建 `sync_db_to_cloud.sh`:

```bash
#!/bin/bash
echo "🔄 同步数据库到云端分支..."

# 确保在主分支并更新数据库
git checkout main
python vectorize_and_store.py
git add db/
git commit -m "更新向量数据库 $(date '+%Y-%m-%d %H:%M:%S')"
git push origin main

# 切换到云端分支并同步数据库
git checkout cloud-deployment
git checkout main -- db/
git add db/
git commit -m "同步数据库文件 $(date '+%Y-%m-%d %H:%M:%S')"
git push origin cloud-deployment

echo "✅ 数据库同步完成！"
```

### 云端自动更新脚本

创建 `update_cloud.sh`:

```bash
#!/bin/bash
echo "🔄 更新云端服务..."

# 拉取最新代码和数据库
git pull origin cloud-deployment

# 重启服务
echo "重启服务中..."
pkill -f app_cloud
sleep 2
nohup python app_cloud.py > app.log 2>&1 &

echo "✅ 服务更新完成！"
echo "📊 查看状态: curl http://localhost:5000/health"
```

## 资源使用情况

### 内存占用
- **启动后**: ~200MB
- **查询时**: ~250MB
- **峰值**: <400MB

### CPU使用
- **空闲**: <5%
- **查询时**: 20-40%
- **并发查询**: 根据请求量动态调整

### 存储空间
- **代码**: ~50MB
- **数据库**: ~200MB
- **总计**: ~250MB

## 服务监控

### 健康检查
```bash
curl http://localhost:5000/health
```

### 服务状态
```json
{
  "status": "healthy",
  "collections_count": 5,
  "available_collections": ["knowledge_base_ming_shi_an_li", ...],
  "llm_enabled": true
}
```

## 故障排除

### 常见问题

1. **数据库文件不存在**
   ```
   错误: ChromaDB数据库文件不存在
   解决: git pull origin cloud-deployment
   ```

2. **集合未找到**
   ```
   错误: 未找到 'xxx' 类型的案例数据
   解决: 检查数据库是否为最新版本，重新同步
   ```

3. **服务无法启动**
   ```
   解决: 检查端口占用，杀死旧进程
   pkill -f app_cloud
   ```

### 日志查看
```bash
# 查看服务日志
tail -f app.log

# 查看系统资源
htop
free -h
```

## 版本管理优势

### Git方式的优点
- ✅ **版本控制**: 数据库变更可追溯
- ✅ **回滚功能**: 可快速回退到之前版本  
- ✅ **分支隔离**: 开发和生产环境分离
- ✅ **自动化**: 支持CI/CD集成
- ✅ **团队协作**: 多人协作更方便

### 分支策略
- `main`: 开发分支，包含完整功能和最新数据
- `cloud-deployment`: 生产分支，仅包含查询功能和稳定数据

## 成本估算

- **1C2G服务器**: ¥50-100/月
- **流量费用**: 根据使用量
- **存储费用**: 可忽略不计
- **总成本**: ¥60-120/月（包含LLM API调用费用）

这个Git管理方案让数据库更新变得更加简单和可控，同时保持了云端服务的轻量级特性！ 