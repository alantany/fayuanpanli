# 法院判例知识库 - Ubuntu部署指南

## 系统要求

### 硬件要求
- **CPU**: 2核心以上
- **内存**: 4GB RAM以上（推荐8GB）
- **存储**: 10GB可用空间以上
- **网络**: 稳定的互联网连接（用于LLM API调用）

### 软件要求
- **操作系统**: Ubuntu 20.04 LTS 或更高版本
- **Python**: 3.8或更高版本
- **Git**: 用于代码管理
- **Git LFS**: 用于大文件管理

## 1. 环境准备

### 1.1 更新系统
```bash
sudo apt update
sudo apt upgrade -y
```

### 1.2 安装基础依赖
```bash
sudo apt install -y python3 python3-pip python3-venv git curl wget
```

### 1.3 安装Git LFS
```bash
curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | sudo bash
sudo apt install git-lfs
git lfs install
```

### 1.4 创建应用用户（推荐）
```bash
sudo adduser --system --group --home /opt/legal-kb legal-kb
sudo usermod -aG sudo legal-kb
```

## 2. 代码部署

### 2.1 切换到应用用户
```bash
sudo su - legal-kb
```

### 2.2 克隆项目
```bash
cd /opt/legal-kb
git clone <your-repository-url> legal-knowledge-base
cd legal-knowledge-base
```

### 2.3 下载大文件（Git LFS）
```bash
git lfs pull
```

## 3. Python环境配置

### 3.1 创建虚拟环境
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3.2 升级pip
```bash
pip install --upgrade pip
```

### 3.3 安装依赖
```bash
pip install -r requirements.txt
```

### 3.4 验证ChromaDB安装
```bash
python3 -c "import chromadb; print('ChromaDB installed successfully')"
```

## 4. 环境配置

### 4.1 创建.env文件
```bash
cp .env.example .env  # 如果有模板文件
# 或者直接创建
nano .env
```

### 4.2 配置环境变量
在`.env`文件中添加以下内容：
```env
# LLM配置
LLM_API_URL=https://openrouter.ai/api/v1/chat/completions
LLM_API_KEY=your_actual_api_key_here
LLM_MODEL_NAME=deepseek/deepseek-r1:free

# Flask配置
FLASK_ENV=production
FLASK_DEBUG=False

# 数据库路径
CHROMA_DATA_PATH=/opt/legal-kb/legal-knowledge-base/db/
```

### 4.3 设置文件权限
```bash
chmod 600 .env
chown legal-kb:legal-kb .env
```

## 5. 测试应用

### 5.1 激活虚拟环境
```bash
source venv/bin/activate
```

### 5.2 测试启动
```bash
python3 app.py
```
访问 `http://localhost:5001` 验证应用是否正常运行。

按 `Ctrl+C` 停止测试服务。

## 6. 生产环境配置

### 6.1 安装Gunicorn
```bash
pip install gunicorn
```

### 6.2 创建Gunicorn配置文件
```bash
nano gunicorn.conf.py
```

添加以下内容：
```python
# gunicorn.conf.py
bind = "127.0.0.1:5001"
workers = 2
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 100
preload_app = True
```

### 6.3 创建systemd服务文件
```bash
sudo nano /etc/systemd/system/legal-kb.service
```

添加以下内容：
```ini
[Unit]
Description=Legal Knowledge Base Flask App
After=network.target

[Service]
Type=notify
User=legal-kb
Group=legal-kb
WorkingDirectory=/opt/legal-kb/legal-knowledge-base
Environment=PATH=/opt/legal-kb/legal-knowledge-base/venv/bin
ExecStart=/opt/legal-kb/legal-knowledge-base/venv/bin/gunicorn -c gunicorn.conf.py app:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 6.4 启动并启用服务
```bash
sudo systemctl daemon-reload
sudo systemctl enable legal-kb
sudo systemctl start legal-kb
sudo systemctl status legal-kb
```

## 7. Nginx反向代理配置

### 7.1 安装Nginx
```bash
sudo apt install nginx -y
```

### 7.2 创建Nginx配置
```bash
sudo nano /etc/nginx/sites-available/legal-kb
```

添加以下内容：
```nginx
server {
    listen 80;
    server_name your_domain.com;  # 替换为您的域名或IP

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }

    # 静态文件缓存
    location /static {
        alias /opt/legal-kb/legal-knowledge-base/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### 7.3 启用站点
```bash
sudo ln -s /etc/nginx/sites-available/legal-kb /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 8. 防火墙配置

### 8.1 配置UFW
```bash
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw --force enable
```

## 9. SSL证书配置（推荐）

### 9.1 安装Certbot
```bash
sudo apt install snapd
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/bin/certbot
```

### 9.2 获取SSL证书
```bash
sudo certbot --nginx -d your_domain.com
```

## 10. 监控和日志

### 10.1 查看应用日志
```bash
# 查看服务状态
sudo systemctl status legal-kb

# 查看实时日志
sudo journalctl -u legal-kb -f

# 查看Nginx日志
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### 10.2 设置日志轮转
```bash
sudo nano /etc/logrotate.d/legal-kb
```

添加：
```
/var/log/legal-kb/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 legal-kb legal-kb
    postrotate
        systemctl reload legal-kb
    endscript
}
```

## 11. 维护和更新

### 11.1 应用更新流程
```bash
# 切换到应用目录
cd /opt/legal-kb/legal-knowledge-base

# 备份当前版本
sudo cp -r . ../backup-$(date +%Y%m%d)

# 拉取最新代码
git pull origin main

# 更新Git LFS文件
git lfs pull

# 激活虚拟环境
source venv/bin/activate

# 更新依赖
pip install -r requirements.txt

# 重启服务
sudo systemctl restart legal-kb
```

### 11.2 数据库备份
```bash
# 创建备份脚本
nano /opt/legal-kb/backup_db.sh
```

添加：
```bash
#!/bin/bash
BACKUP_DIR="/opt/legal-kb/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
tar -czf $BACKUP_DIR/chroma_backup_$DATE.tar.gz db/
find $BACKUP_DIR -name "chroma_backup_*.tar.gz" -mtime +7 -delete
```

设置权限并添加到crontab：
```bash
chmod +x /opt/legal-kb/backup_db.sh
crontab -e
# 添加：每天凌晨2点备份
0 2 * * * /opt/legal-kb/backup_db.sh
```

## 12. 故障排除

### 12.1 常见问题

**问题**: 应用无法启动
```bash
# 检查错误日志
sudo journalctl -u legal-kb --no-pager -l

# 检查端口占用
sudo netstat -tlnp | grep :5001

# 手动测试
cd /opt/legal-kb/legal-knowledge-base
source venv/bin/activate
python3 app.py
```

**问题**: ChromaDB权限错误
```bash
# 修复权限
sudo chown -R legal-kb:legal-kb /opt/legal-kb/legal-knowledge-base/db/
sudo chmod -R 755 /opt/legal-kb/legal-knowledge-base/db/
```

**问题**: LLM API连接失败
```bash
# 检查网络连接
curl -I https://openrouter.ai

# 验证API密钥
cat .env | grep LLM_API_KEY
```

### 12.2 性能优化

**增加Gunicorn工作进程**：
```python
# 在gunicorn.conf.py中调整
workers = 4  # 根据CPU核心数调整
```

**启用Nginx缓存**：
```nginx
# 在/etc/nginx/sites-available/legal-kb中添加
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=legal_kb_cache:10m;

location / {
    proxy_cache legal_kb_cache;
    proxy_cache_valid 200 1h;
    # ... 其他配置
}
```

## 13. 安全建议

1. **定期更新系统和依赖**
2. **使用强密码和SSH密钥认证**
3. **限制API密钥权限**
4. **定期检查日志异常**
5. **设置监控告警**

## 支持

如遇到部署问题，请查看：
1. 应用日志：`sudo journalctl -u legal-kb -f`
2. Nginx日志：`/var/log/nginx/error.log`
3. 系统资源：`htop` 或 `top`

---

**部署完成后，访问您的域名或IP地址即可使用法院判例知识库系统！** 