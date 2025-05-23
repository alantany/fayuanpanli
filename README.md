# 法院判例知识库 部署说明

## 1. 创建并激活Python虚拟环境

```bash
python3 -m venv venv
source venv/bin/activate
```

## 2. 安装依赖

```bash
pip install -r requirements.txt
```

## 3. 运行主要脚本

- 提取PDF判例并保存为.md文件：
  ```bash
  python extract_cases.py
  ```
- 构建向量索引：
  ```bash
  python build_index.py
  ```
- 启动Web检索服务（可选）：
  ```bash
  python app.py
  ```

## 4. 目录结构建议

```
/当前目录
  ├─ pdfs/           # 原始PDF文件
  ├─ cases_md/       # 自动生成的判例.md文件
  ├─ extract_cases.py
  ├─ build_index.py
  ├─ app.py
  ├─ requirements.txt
  └─ README.md
```

---
如需详细脚本或有其他定制需求，请联系开发者。 