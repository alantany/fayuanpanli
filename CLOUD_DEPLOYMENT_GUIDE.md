# 法院判例知识库 - 云端轻量级部署指南

## 概述

本指南适用于1C2G云服务器的轻量级部署，通过使用远程embedding API替代本地模型，大幅降低资源需求。

## 系统要求

### 最低配置
- **CPU**: 1核心
- **内存**: 2GB RAM
- **存储**: 5GB可用空间
- **网络**: 稳定的互联网连接（用于API调用）

### 软件要求
- **操作系统**: Ubuntu 20.04 LTS 或更高版本
- **Python**: 3.8或更高版本
- **Git**: 用于代码管理

## 部署步骤

### 1. 环境准备

#### 1.1 更新系统
```bash
sudo apt update
sudo apt upgrade -y
```

#### 1.2 安装基础依赖
```bash
sudo apt install -y python3 python3-pip python3-venv git curl wget
```

#### 1.3 创建应用目录
```bash
sudo mkdir -p /opt/legal-kb
cd /opt/legal-kb
```

### 2. 代码部署

#### 2.1 克隆项目（云端分支）
```bash
git clone -b cloud-deployment <your-repository-url> legal-knowledge-base
cd legal-knowledge-base
```

#### 2.2 创建虚拟环境
```bash
python3 -m venv venv
source venv/bin/activate
```

#### 2.3 安装云端依赖
```bash
pip install --upgrade pip
pip install -r requirements-cloud.txt
```

### 3. 配置环境变量

#### 3.1 创建配置文件
```bash
cp env_cloud_template.txt .env
nano .env
```

#### 3.2 配置必要的API密钥
编辑`.env`文件，填入以下必要信息：

```env
# 必须配置
EMBEDDING_API_KEY=your_actual_openai_api_key
LLM_API_KEY=your_actual_llm_api_key

# 可选优化配置
BATCH_SIZE=5          # 如果内存不足，可以降到5
MEMORY_LIMIT=1200     # 根据实际内存调整
```

#### 3.3 设置文件权限
```bash
chmod 600 .env
```

### 4. 数据准备

#### 4.1 方案A: 使用现有数据库
如果您已有ChromaDB数据库文件：
```bash
# 上传现有的db/目录到服务器
scp -r local_db/ user@server:/opt/legal-kb/legal-knowledge-base/db/
```

#### 4.2 方案B: 重新向量化（推荐）
使用云端API重新向量化数据：
```bash
# 确保案例文件已上传
# 运行云端向量化脚本
python3 vectorize_and_store_cloud.py
```

### 5. 测试应用

#### 5.1 激活虚拟环境
```bash
source venv/bin/activate
```

#### 5.2 测试启动
```bash
python3 app_cloud.py
```

#### 5.3 健康检查
```bash
curl http://localhost:5001/health
```

预期返回：
```json
{
  "status": "healthy",
  "services": {
    "chromadb": true,
    "embedding_service": true,
    "llm_enabled": true
  },
  "memory": {
    "rss_mb": 150.5,
    "vms_mb": 280.3
  }
}
```

### 6. 生产环境配置

#### 6.1 安装Gunicorn
```bash
pip install gunicorn
```

#### 6.2 创建Gunicorn配置
```bash
nano gunicorn_cloud.conf.py
```

内容：
```python
# gunicorn_cloud.conf.py - 1C2G优化配置
bind = "127.0.0.1:5001"
workers = 1                    # 单核单进程
worker_class = "sync"
worker_connections = 100       # 降低连接数
timeout = 120
keepalive = 2
max_requests = 500             # 降低最大请求数
max_requests_jitter = 50
preload_app = True
worker_tmp_dir = "/dev/shm"    # 使用内存临时目录
```

#### 6.3 创建systemd服务
```bash
sudo nano /etc/systemd/system/legal-kb-cloud.service
```

内容：
```ini
[Unit]
Description=Legal Knowledge Base Cloud Flask App
After=network.target

[Service]
Type=notify
User=root
Group=root
WorkingDirectory=/opt/legal-kb/legal-knowledge-base
Environment=PATH=/opt/legal-kb/legal-knowledge-base/venv/bin
ExecStart=/opt/legal-kb/legal-knowledge-base/venv/bin/gunicorn -c gunicorn_cloud.conf.py app_cloud:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=10
MemoryLimit=1.8G
CPUQuota=100%

[Install]
WantedBy=multi-user.target
```

#### 6.4 启动服务
```bash
sudo systemctl daemon-reload
sudo systemctl enable legal-kb-cloud
sudo systemctl start legal-kb-cloud
sudo systemctl status legal-kb-cloud
```

### 7. Nginx配置（可选）

#### 7.1 安装Nginx
```bash
sudo apt install nginx -y
```

#### 7.2 创建配置文件
```bash
sudo nano /etc/nginx/sites-available/legal-kb-cloud
```

内容：
```nginx
server {
    listen 80;
    server_name your_domain_or_ip;

    # 限制请求大小
    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时设置
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
        proxy_connect_timeout 10s;
        
        # 缓冲设置
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    # 健康检查端点
    location /health {
        proxy_pass http://127.0.0.1:5001/health;
        access_log off;
    }

    # 静态文件（如果有）
    location /static {
        alias /opt/legal-kb/legal-knowledge-base/static;
        expires 1d;
        add_header Cache-Control "public, immutable";
    }
}
```

#### 7.3 启用站点
```bash
sudo ln -s /etc/nginx/sites-available/legal-kb-cloud /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 性能优化

### 1. 内存优化

#### 1.1 启用swap（如果需要）
```bash
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

#### 1.2 调整系统参数
```bash
# 编辑 /etc/sysctl.conf
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
echo 'vm.vfs_cache_pressure=50' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### 2. API优化

#### 2.1 启用缓存
确保`.env`中设置：
```env
ENABLE_EMBEDDING_CACHE=True
CACHE_MAX_SIZE_MB=50  # 根据可用空间调整
```

#### 2.2 调整批处理大小
如果内存不足，降低批处理大小：
```env
BATCH_SIZE=3
```

### 3. 监控设置

#### 3.1 创建监控脚本
```bash
nano /opt/legal-kb/monitor.sh
```

内容：
```bash
#!/bin/bash
# 简单的资源监控脚本

LOG_FILE="/var/log/legal-kb-monitor.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# 获取内存使用
MEMORY_USAGE=$(free -m | awk 'NR==2{printf "%.1f%%", $3*100/$2}')

# 获取CPU使用
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}')

# 检查服务状态
SERVICE_STATUS=$(systemctl is-active legal-kb-cloud)

# 记录日志
echo "[$DATE] Memory: $MEMORY_USAGE, CPU: $CPU_USAGE%, Service: $SERVICE_STATUS" >> $LOG_FILE

# 如果内存使用超过90%，重启服务
MEMORY_NUM=$(echo $MEMORY_USAGE | sed 's/%//')
if (( $(echo "$MEMORY_NUM > 90" | bc -l) )); then
    echo "[$DATE] High memory usage detected, restarting service..." >> $LOG_FILE
    systemctl restart legal-kb-cloud
fi
```

#### 3.2 设置定时任务
```bash
chmod +x /opt/legal-kb/monitor.sh
crontab -e
# 添加：每5分钟检查一次
*/5 * * * * /opt/legal-kb/monitor.sh
```

## 故障排除

### 1. 常见问题

#### 问题1: 内存不足
```bash
# 检查内存使用
free -h
# 检查进程内存使用
ps aux --sort=-%mem | head

# 解决方案：
# 1. 降低BATCH_SIZE
# 2. 启用swap
# 3. 重启服务释放内存
sudo systemctl restart legal-kb-cloud
```

#### 问题2: API调用失败
```bash
# 检查网络连接
curl -I https://api.openai.com
# 检查API密钥
grep EMBEDDING_API_KEY .env

# 解决方案：
# 1. 验证API密钥有效性
# 2. 检查API配额
# 3. 查看应用日志
sudo journalctl -u legal-kb-cloud -f
```

#### 问题3: 服务启动失败
```bash
# 查看详细错误
sudo journalctl -u legal-kb-cloud --no-pager -l

# 手动测试
cd /opt/legal-kb/legal-knowledge-base
source venv/bin/activate
python3 app_cloud.py
```

### 2. 日志查看

```bash
# 应用日志
sudo journalctl -u legal-kb-cloud -f

# Nginx日志
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# 系统资源
htop
```

## 成本估算

### API调用成本（以OpenAI为例）

- **Embedding API**: text-embedding-3-small
  - 价格: $0.00002 / 1K tokens
  - 估算: 1000个案例 ≈ $0.5-2
  
- **查询成本**: 每次查询 ≈ $0.0001-0.0005

### 服务器成本
- **1C2G云服务器**: ¥30-100/月（根据提供商）

## 维护建议

1. **定期备份数据库**
2. **监控API使用量**
3. **定期更新依赖包**
4. **监控系统资源使用**
5. **设置告警机制**

---

**部署完成后，您的法院判例知识库将在低资源环境下高效运行！** 