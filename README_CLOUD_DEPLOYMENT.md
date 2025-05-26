# 法院判例知识库 - 云端轻量级部署分支

## 🎯 分支目标

本分支 `cloud-deployment` 专门为1C2G云服务器环境优化，通过使用远程embedding API替代本地模型，将内存需求从4GB降至1.5GB以下。

## 📊 资源对比

| 项目 | 原版本 | 云端版本 | 优化效果 |
|------|--------|----------|----------|
| 内存需求 | 4GB+ | 1.5GB以下 | 降低62% |
| 存储空间 | 10GB+ | 5GB | 减少50% |
| 启动时间 | 60秒+ | 10秒内 | 提升83% |
| 服务器要求 | 4C8G | 1C2G | 成本降低75% |

## 🚀 新增功能

### 1. 远程Embedding服务
- **多API支持**: OpenAI、Azure OpenAI、Cohere
- **智能缓存**: 减少重复API调用，降低成本
- **自动重试**: 网络异常时的容错机制
- **Token管理**: 自动截断过长文本

### 2. 资源优化
- **内存监控**: 实时监控内存使用情况
- **批处理优化**: 可配置的批处理大小
- **垃圾回收**: 主动内存清理机制
- **进程限制**: systemd资源限制配置

### 3. 生产就绪
- **健康检查**: `/health` 端点监控服务状态
- **日志管理**: 结构化日志和轮转配置
- **监控脚本**: 自动重启和告警机制
- **部署自动化**: 完整的部署脚本和配置

## 📁 新增文件

```
cloud-deployment/
├── requirements-cloud.txt          # 云端专用依赖
├── config_cloud.py                 # 云端配置管理
├── embedding_service.py            # 统一embedding服务接口
├── vectorize_and_store_cloud.py    # 云端向量化脚本
├── app_cloud.py                    # 云端Flask应用
├── env_cloud_template.txt          # 环境变量模板
├── CLOUD_DEPLOYMENT_PLAN.md        # 技术改造方案
├── CLOUD_DEPLOYMENT_GUIDE.md       # 详细部署指南
└── README_CLOUD_DEPLOYMENT.md      # 本文档
```

## 🛠️ 快速开始

### 1. 克隆云端分支
```bash
git clone -b cloud-deployment https://github.com/alantany/fayuanpanli.git
cd fayuanpanli
```

### 2. 安装依赖
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-cloud.txt
```

### 3. 配置环境
```bash
cp env_cloud_template.txt .env
# 编辑 .env 文件，填入您的API密钥
nano .env
```

### 4. 启动应用
```bash
python3 app_cloud.py
```

### 5. 健康检查
```bash
curl http://localhost:5001/health
```

## 🔧 配置说明

### 必需配置
```env
EMBEDDING_API_KEY=your_openai_api_key_here
LLM_API_KEY=your_llm_api_key_here
```

### 性能调优
```env
BATCH_SIZE=10          # 批处理大小，内存不足时可降至3-5
MEMORY_LIMIT=1500      # 内存限制(MB)
ENABLE_EMBEDDING_CACHE=True  # 启用缓存
```

## 💰 成本估算

### API成本（OpenAI text-embedding-3-small）
- **初始向量化**: 1000个案例 ≈ $0.5-2
- **日常查询**: 每次查询 ≈ $0.0001-0.0005
- **月度估算**: 1000次查询/月 ≈ $0.1-0.5

### 服务器成本
- **1C2G云服务器**: ¥30-100/月
- **总成本**: ¥30-100/月（相比4C8G节省75%）

## 📈 性能特点

### 优势
- ✅ 极低资源需求，适合小型云服务器
- ✅ 使用最新embedding模型，准确性更高
- ✅ 智能缓存机制，降低API调用成本
- ✅ 完整的监控和故障恢复机制
- ✅ 生产环境就绪的配置

### 权衡
- ⚠️ 查询延迟增加200-500ms（API调用）
- ⚠️ 需要稳定的网络连接
- ⚠️ 依赖第三方API服务

## 🔍 监控和维护

### 健康检查
```bash
curl http://localhost:5001/health
```

### 查看日志
```bash
sudo journalctl -u legal-kb-cloud -f
```

### 内存监控
```bash
free -h
ps aux --sort=-%mem | head
```

## 🆘 故障排除

### 常见问题
1. **内存不足**: 降低 `BATCH_SIZE` 或启用swap
2. **API调用失败**: 检查网络连接和API密钥
3. **服务启动失败**: 查看详细日志排查问题

### 获取帮助
- 查看 `CLOUD_DEPLOYMENT_GUIDE.md` 获取详细部署指南
- 检查应用日志: `sudo journalctl -u legal-kb-cloud -f`
- GitHub Issues: https://github.com/alantany/fayuanpanli/issues

## 🔄 从主分支迁移

如果您已经在使用主分支，可以通过以下步骤迁移：

1. **备份现有数据**
```bash
cp -r db/ db_backup/
```

2. **切换到云端分支**
```bash
git checkout cloud-deployment
```

3. **重新向量化数据**（推荐）
```bash
python3 vectorize_and_store_cloud.py
```

4. **或复制现有数据库**
```bash
cp -r db_backup/ db/
```

## 📞 技术支持

- **GitHub仓库**: https://github.com/alantany/fayuanpanli
- **云端分支**: https://github.com/alantany/fayuanpanli/tree/cloud-deployment
- **部署指南**: [CLOUD_DEPLOYMENT_GUIDE.md](CLOUD_DEPLOYMENT_GUIDE.md)
- **技术方案**: [CLOUD_DEPLOYMENT_PLAN.md](CLOUD_DEPLOYMENT_PLAN.md)

---

**🎉 享受您的轻量级法院判例知识库！** 