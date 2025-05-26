# 法院判例知识库 - Git部署使用指南

## 🎉 新功能：Git管理数据库

现在数据库文件已纳入Git管理，部署更加简单！

## 📋 快速使用

### 本地开发 (main分支)
```bash
# 添加新案例后，重新生成数据库
python vectorize_and_store.py

# 提交更改
git add .
git commit -m "添加新案例"
git push origin main
```

### 同步到云端分支
```bash
# 使用自动化脚本（推荐）
./sync_db_to_cloud.sh

# 或手动操作
git checkout cloud-deployment
git checkout main -- db/
git add db/
git commit -m "同步数据库文件"
git push origin cloud-deployment
```

### 云端部署
```bash
# 一键部署
git clone https://github.com/alantany/fayuanpanli.git
cd fayuanpanli
git checkout cloud-deployment
pip install -r requirements-cloud.txt
python app_cloud.py

# 或使用自动化脚本更新
./update_cloud.sh
```

## 🔄 数据库更新流程

1. **本地**: 添加案例 → 运行向量化 → 提交推送
2. **同步**: 运行 `./sync_db_to_cloud.sh`
3. **云端**: 运行 `git pull origin cloud-deployment` 或 `./update_cloud.sh`

## ✨ 主要优势

- ✅ **无需手动打包**: 告别tar压缩上传
- ✅ **版本控制**: 数据库变更可追溯和回滚
- ✅ **自动化脚本**: 一键同步和部署
- ✅ **分支隔离**: 开发和生产环境完全分离
- ✅ **简化运维**: Git pull即可更新数据库

## 📁 分支说明

- `main`: 开发分支，包含完整功能
- `cloud-deployment`: 生产分支，仅查询功能，包含数据库文件

现在云端部署变得像更新代码一样简单！🚀 