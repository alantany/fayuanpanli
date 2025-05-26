# 法院判例知识库 - 云端查询服务部署指南

## 概述

这是一个专为1C2G云服务器优化的**查询专用版本**，不包含embedding功能，仅提供向量数据库查询服务。

## 架构特点

- ✅ **轻量级**: 移除了所有embedding模型和依赖
- ✅ **低资源**: 适合1C2G服务器运行
- ✅ **查询专用**: 只提供搜索和LLM分析功能
- ✅ **预处理分离**: 向量化在本地完成，云端只需数据库文件

## 部署步骤

### 1. 本地准备向量数据库

在本地运行完整版本，生成向量数据库：

```bash
# 在本地主分支
git checkout main
python vectorize_and_store.py
```

### 2. 打包数据库文件

```bash
# 压缩数据库目录
tar -czf db.tar.gz db/
```

### 3. 云端部署

```bash
# 1. 克隆代码到云端服务器
git clone https://github.com/你的用户名/fayuanpanli.git
cd fayuanpanli
git checkout cloud-deployment

# 2. 上传并解压数据库文件
scp db.tar.gz 用户名@服务器IP:/path/to/fayuanpanli/
tar -xzf db.tar.gz

# 3. 安装依赖
pip install -r requirements-cloud.txt

# 4. 设置环境变量（可选LLM分析）
export LLM_API_URL="你的LLM_API地址"
export LLM_API_KEY="你的API密钥"
export LLM_MODEL_NAME="模型名称"

# 5. 启动服务
chmod +x start_cloud.sh
./start_cloud.sh
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

## 更新数据库

当需要更新案例数据时：

1. **本地更新**: 在主分支添加新案例，重新运行向量化
2. **打包上传**: 重新打包db目录并上传到云端
3. **重启服务**: 重启云端服务以加载新数据

```bash
# 云端重启
pkill gunicorn
./start_cloud.sh
```

## 故障排除

### 常见问题

1. **数据库文件不存在**
   ```
   错误: ChromaDB数据库文件不存在
   解决: 确保db/chroma.sqlite3文件存在
   ```

2. **集合未找到**
   ```
   错误: 未找到 'xxx' 类型的案例数据
   解决: 检查本地向量化是否成功完成
   ```

3. **内存不足**
   ```
   解决: 减少gunicorn workers数量到1个
   ```

### 日志查看
```bash
# 查看服务日志
tail -f nohup.out

# 查看系统资源
htop
free -h
```

## 性能优化建议

1. **数据库优化**
   - 定期清理不需要的集合
   - 压缩数据库文件

2. **服务配置**
   - 使用单worker模式
   - 设置合理的超时时间
   - 启用请求限制

3. **系统级优化**
   - 配置swap空间
   - 调整系统内存参数

## 成本估算

- **1C2G服务器**: ¥50-100/月
- **流量费用**: 根据使用量
- **总成本**: ¥60-120/月（包含LLM API调用费用）

这个方案可以大大降低云端服务器的资源需求和成本，同时保持完整的查询功能。 