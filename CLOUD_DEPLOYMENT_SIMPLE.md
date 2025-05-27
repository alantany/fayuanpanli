# 法院判例知识库 - 云端部署指南（简化版）

## 概述

本版本专为云端1C2G服务器优化，支持高效的案例查询和大模型分析功能。

### 主要特性
- ✅ 轻量级部署（内存使用 < 500MB）
- ✅ 中文语义搜索支持
- ✅ 大模型分析功能
- ✅ 跨平台数据库兼容性
- ✅ 自动fallback复制功能（支持HTTP环境）

### 架构说明
- **本地环境**：负责数据处理和向量化，生成数据库文件
- **云端环境**：专注查询服务，使用轻量级embedding模型确保搜索准确性

## 快速部署

### 1. 克隆代码
```bash
git clone https://github.com/alantany/fayuanpanli.git
cd fayuanpanli
git checkout cloud-deployment
```

### 2. 安装依赖
```bash
pip install -r requirements-cloud.txt
```

### 3. 配置环境变量
创建 `.env` 文件：
```bash
# 大模型配置（可选）
LLM_API_KEY=your_api_key_here
LLM_API_URL=https://api.openai.com/v1/chat/completions
LLM_MODEL_NAME=gpt-3.5-turbo
```

### 4. 启动服务
```bash
python app_cloud.py
```

## 搜索功能说明

### 智能搜索机制
系统会自动检测并选择最佳搜索方式：

1. **优先使用embedding搜索**：
   - 加载轻量级中文embedding模型
   - 支持语义相似度搜索
   - 能理解"婚姻"、"离婚"、"夫妻关系"等相关概念

2. **备用文本搜索**：
   - 如果embedding模型加载失败
   - 自动降级到关键词匹配搜索

### 搜索效果对比

**使用embedding搜索**：
- 查询："婚姻纠纷" → 返回：离婚案例、财产分割案例
- 查询："合同违约" → 返回：买卖合同纠纷、服务合同纠纷

**不使用embedding搜索**：
- 查询："婚姻纠纷" → 可能返回：包含"婚姻"字样的任意案例
- 搜索准确性大幅下降

## 性能优化

### 资源使用
- **内存占用**：300-500MB（包含embedding模型）
- **启动时间**：15-30秒（首次下载模型）
- **查询响应**：< 1秒

### 模型缓存
- embedding模型会自动缓存到本地
- 后续启动无需重新下载
- 模型大小：约120MB

## 故障排除

### 1. 搜索结果不准确
检查日志中的搜索方式：
```bash
# 期望看到：
[INFO] Using embedding model for vector search

# 如果看到：
[INFO] Using ChromaDB default text search
# 说明embedding模型未加载成功
```

### 2. 内存不足
如果服务器内存不足，可以禁用embedding：
```python
# 在app_cloud.py中设置
EMBEDDING_AVAILABLE = False
```

### 3. 模型下载失败
手动下载模型：
```bash
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"
```

## 监控和维护

### 健康检查
```bash
curl http://your-server:5000/health
```

### 日志监控
```bash
tail -f app.log
```

### 性能监控
```bash
# 查看内存使用
ps aux | grep python

# 查看端口占用
netstat -tlnp | grep 5000
```

## 更新部署

### 更新代码
```bash
cd fayuanpanli
git pull origin cloud-deployment
pip install -r requirements-cloud.txt
python app_cloud.py
```

### 更新数据库
```bash
# 如果本地有新的数据库文件
git pull origin cloud-deployment
# 数据库文件会自动更新
```

## 技术说明

### Embedding模型选择
- **模型**：`paraphrase-multilingual-MiniLM-L12-v2`
- **优势**：支持中文、体积小（120MB）、速度快
- **性能**：在1C2G环境下运行良好

### 搜索算法
- 使用余弦相似度计算语义相似性
- 支持跨语言搜索（中英文混合）
- 自动处理同义词和相关概念

---

**注意**：首次启动时会下载embedding模型，请确保网络连接正常。 
这个Git管理方案让数据库更新变得更加简单和可控，同时保持了云端服务的轻量级特性！ 