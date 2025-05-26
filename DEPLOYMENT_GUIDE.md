# 法院判例知识库系统部署指南

## 1. 系统要求
- Ubuntu 20.04 LTS 或更高版本
- Python 3.9 或更高版本
- Git
- Git LFS

## 2. 环境准备

### 2.1 安装系统依赖
```bash
# 更新系统包
sudo apt update
sudo apt upgrade -y

# 安装 Python 和必要的系统包
sudo apt install -y python3.9 python3.9-venv python3-pip git git-lfs

# 安装 Git LFS
git lfs install
```

### 2.2 克隆项目
```bash
# 克隆项目代码
git clone https://github.com/alantany/fayuanpanli
cd fayuanpanli

# 拉取 LFS 文件
git lfs pull
```

### 2.3 创建并激活虚拟环境
```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate
```

### 2.4 安装项目依赖
```bash
# 安装依赖包
pip install -r requirements.txt
```

## 3. 数据库初始化

### 3.1 准备数据目录
```bash
# 创建数据目录
mkdir -p db
```

### 3.2 初始化向量数据库
```bash
# 运行向量化脚本
python vectorize_and_store.py
```

如果遇到数据库损坏或需要重新创建，请按以下步骤操作：
1. 备份当前数据库（可选）：
```bash
mv db db_backup_$(date +%Y%m%d_%H%M%S)
```

2. 重新创建数据库：
```bash
# 确保数据目录存在
mkdir -p db

# 运行向量化脚本
python vectorize_and_store.py
```

3. 验证数据库状态：
```bash
python test_db.py
```

## 4. 配置环境变量

### 4.1 创建环境变量文件
```bash
# 复制环境变量模板
cp .env.template .env
```

### 4.2 编辑环境变量
使用文本编辑器编辑 `.env` 文件，设置必要的环境变量：
```bash
nano .env
```

确保设置以下变量：
- LLM_API_URL：大模型 API 地址
- LLM_API_KEY：大模型 API 密钥
- LLM_MODEL_NAME：使用的模型名称

## 5. 启动应用

### 5.1 开发环境启动
```bash
# 确保在虚拟环境中
source venv/bin/activate

# 启动 Flask 应用
python app.py
```

### 5.2 生产环境部署
推荐使用 Gunicorn 作为 WSGI 服务器：

1. 安装 Gunicorn：
```bash
pip install gunicorn
```

2. 创建 Gunicorn 配置文件：
```bash
# 创建配置文件
cat > gunicorn_config.py << EOF
bind = "0.0.0.0:5001"
workers = 4
timeout = 120
EOF
```

3. 使用 systemd 管理服务：
```bash
# 创建服务文件
sudo nano /etc/systemd/system/case-knowledge-base.service
```

添加以下内容：
```ini
[Unit]
Description=Case Knowledge Base System
After=network.target

[Service]
User=<your-username>
WorkingDirectory=/path/to/法院判例知识库
Environment="PATH=/path/to/法院判例知识库/venv/bin"
ExecStart=/path/to/法院判例知识库/venv/bin/gunicorn -c gunicorn_config.py app:app

[Install]
WantedBy=multi-user.target
```

4. 启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl start case-knowledge-base
sudo systemctl enable case-knowledge-base
```

## 6. 维护和故障排除

### 6.1 查看日志
```bash
# 查看应用日志
sudo journalctl -u case-knowledge-base -f
```

### 6.2 数据库维护
如果遇到数据库问题，可以：
1. 检查数据库状态：
```bash
python test_db.py
```

2. 重新创建数据库：
```bash
# 备份当前数据库
mv db db_backup_$(date +%Y%m%d_%H%M%S)

# 重新创建数据库
python vectorize_and_store.py
```

### 6.3 常见问题解决
1. 如果遇到权限问题：
```bash
sudo chown -R <your-username>:<your-group> /path/to/法院判例知识库
```

2. 如果遇到端口占用：
```bash
# 检查端口占用
sudo lsof -i :5001

# 如果需要，可以修改 gunicorn_config.py 中的端口
```

## 7. 备份策略

### 7.1 数据库备份
```bash
# 创建备份目录
mkdir -p backups

# 备份数据库
cp -r db backups/db_$(date +%Y%m%d_%H%M%S)
```

### 7.2 代码备份
```bash
# 备份代码
tar -czf backups/code_$(date +%Y%m%d_%H%M%S).tar.gz .
```

## 8. 安全建议
1. 定期更新系统和依赖包
2. 使用防火墙限制访问
3. 定期备份数据
4. 使用 HTTPS 进行安全访问
5. 妥善保管 API 密钥和敏感信息 