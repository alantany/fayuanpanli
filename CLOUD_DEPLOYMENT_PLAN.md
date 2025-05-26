# 法院判例知识库 - 云端轻量级部署方案

## 目标
将现有系统改造为适合1C2G云服务器的轻量级版本，主要通过使用远程embedding API替代本地模型来降低资源需求。

## 技术改造方案

### 1. 核心改动
- **移除本地embedding模型**: 不再使用`sentence-transformers`本地模型
- **使用远程embedding API**: 集成OpenAI或其他云端embedding服务
- **保持ChromaDB**: 继续使用ChromaDB作为向量数据库
- **优化内存使用**: 减少批处理大小，优化数据加载

### 2. 新增依赖
```
openai>=1.0.0  # 用于embedding API调用
tiktoken       # 用于token计算
```

### 3. 移除依赖
```
sentence-transformers  # 本地模型，占用大量内存
torch                  # PyTorch依赖，内存占用大
```

### 4. 环境变量配置
```env
# Embedding API配置
EMBEDDING_API_PROVIDER=openai  # 或 azure, cohere等
EMBEDDING_API_KEY=your_embedding_api_key
EMBEDDING_MODEL_NAME=text-embedding-3-small
EMBEDDING_API_URL=https://api.openai.com/v1/embeddings

# 性能优化配置
BATCH_SIZE=10          # 降低批处理大小
MAX_WORKERS=1          # 限制并发数
MEMORY_LIMIT=1500      # 内存限制(MB)
```

## 文件修改清单

### 1. requirements-cloud.txt (新建)
专门用于云端部署的依赖文件，移除重型依赖。

### 2. embedding_service.py (新建)
统一的embedding服务接口，支持多种远程API。

### 3. vectorize_and_store_cloud.py (修改)
修改向量化脚本，使用远程embedding API。

### 4. app_cloud.py (修改)
修改Flask应用，使用新的embedding服务。

### 5. config_cloud.py (新建)
云端部署专用配置文件。

## 部署流程

### 阶段1: 代码改造
1. 创建新的依赖文件
2. 实现远程embedding服务
3. 修改向量化脚本
4. 修改Flask应用
5. 创建云端配置

### 阶段2: 数据迁移
1. 在本地重新向量化数据（使用远程API）
2. 上传新的ChromaDB数据库到云端
3. 验证数据完整性

### 阶段3: 云端部署
1. 在云服务器上部署新版本
2. 配置环境变量
3. 启动服务并测试

## 资源优化策略

### 1. 内存优化
- 使用流式处理，避免一次性加载大量数据
- 实现内存监控和自动清理
- 优化ChromaDB配置

### 2. 网络优化
- 实现embedding结果缓存
- 批量API调用减少网络开销
- 错误重试机制

### 3. 成本控制
- 选择性价比高的embedding API
- 实现请求频率限制
- 监控API使用量

## 预期效果

### 资源需求降低
- **内存使用**: 从4GB降至1.5GB以下
- **存储空间**: 减少约2GB（移除模型文件）
- **启动时间**: 从60秒降至10秒以内

### 性能影响
- **查询延迟**: 增加200-500ms（API调用）
- **并发能力**: 受API限制，但对单用户影响小
- **准确性**: 保持相同或更好（使用更先进的embedding模型）

## 风险评估

### 1. 技术风险
- **API依赖**: 需要稳定的网络连接
- **成本控制**: API调用费用需要监控
- **兼容性**: 确保embedding维度一致

### 2. 缓解措施
- 实现本地缓存机制
- 设置API使用限额
- 提供降级方案

## 开发时间估算
- **代码改造**: 2-3天
- **测试验证**: 1天
- **部署调试**: 1天
- **总计**: 4-5天 