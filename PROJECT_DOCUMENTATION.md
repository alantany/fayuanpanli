# 法院判例知识库项目文档

## 1. 项目目标

本项目旨在构建一个智能的法院判例知识库系统。该系统能够处理五种不同类型的法律案例（民事案例、刑事案例、行政案例、执行案例、国家赔偿案例），并允许司法人员通过自然语言查询，快速找到相关的案例作为参考。

## 2. 系统架构

系统主要包括数据处理、知识库构建和查询接口三个核心部分。

### 2.1 数据来源

*   五份包含不同类型案例的原始文档（最初为PDF，现已处理为 `.txt` 文件集合）。
    *   民事案例
    *   刑事案例
    *   行政案例
    *   执行案例
    *   国家赔偿案例

### 2.2 数据处理与准备流程

1.  **文本提取与初步整合**：
    *   原始PDF内容被提取并整合为各大类下的 `all_cases.txt` 文件。
    *   脚本：`extract_cases.py` (此脚本的PDF提取部分已完成，主要复用其文本处理逻辑)
2.  **内容清理**：
    *   针对 `all_cases.txt` 或已分割的案例文件，移除特定的元信息字符串（如 "指导案例 号："）和标准化的ID及页码串。
    *   脚本：`clean_single_all_cases_file.py` (用于清理 `all_cases.txt` 文件)
    *   脚本：`clean_guiding_cases.py` (用于清理特定目录下已分割的文件)
    *   脚本：`clean_civil_case_ids.py` (早期用于清理民事案例中特定ID的脚本)
3.  **案例分割**：
    *   将清理后的 `all_cases.txt` 文件按案件（以 `【` 为分隔符）分割成独立的 `.txt` 文件，并根据案件名规范化命名。
    *   这些文件存储在各自案例类型下的 `cases/`子目录中 (例如 `民事案例/cases/`, `行政案例/cases/` 等)。
    *   脚本：`extract_cases.py`

### 2.3 知识库构建

1.  **向量化模型**：
    *   使用 `sentence-transformers` 库中的预训练模型将每个案例的文本内容转换为高维向量。
2.  **向量存储**：
    *   使用 `ChromaDB` 作为向量数据库。
    *   为五种案例类型分别创建独立的 ChromaDB **集合 (Collection)**，例如：
        *   `civil_cases_collection`
        *   `criminal_cases_collection`
        *   `administrative_cases_collection`
        *   `enforcement_cases_collection`
        *   `state_compensation_cases_collection`
    *   每个案例向量及其元数据（如原始文件名、案件类型）将被存入对应的集合中。ChromaDB 会将数据持久化到磁盘。

### 2.4 查询接口

1.  **前端界面**：
    *   构建一个简单的Web用户界面，使用 `Flask` 框架。
    *   界面包含一个文本输入框供用户输入查询语句。
    *   提供一个下拉菜单，让用户选择要查询的案例类型（民事、刑事、行政、执行、国家赔偿）。
2.  **后端逻辑**：
    *   Flask应用接收前端的查询请求和选定的案例类型。
    *   根据选定的案例类型，连接到对应的ChromaDB集合。
    *   将用户查询语句向量化。
    *   在选定的ChromaDB集合中执行相似性搜索，检索最相关的 `k` 个案例。
    *   将检索结果（例如，案例文件名和/或部分文本内容）返回给前端展示。

## 3. 核心组件与脚本

*   **`requirements.txt`**: 列出项目所需的Python依赖库（如 `sentence-transformers`, `chromadb`, `flask`, `pdfplumber`）。
*   **`.gitignore`**: 指定Git版本控制系统应忽略的文件和目录（如 `venv/`, `__pycache__/`, ChromaDB的持久化数据目录等）。
*   **`extract_cases.py`**:
    *   功能：从PDF提取文本（早期功能），更主要的是将 `all_cases.txt` 类型的总文件按 `【` 分割成独立的案例文件，并按规则命名。
*   **`clean_single_all_cases_file.py`**:
    *   功能：清理单个大型文本文件（如 `all_cases.txt`），移除特定的元信息字符串和ID串。
*   **`clean_guiding_cases.py`**:
    *   功能：清理已分割的、位于特定目录下的多个案例 `.txt` 文件，并根据内容重命名这些文件。
*   **`vectorize_and_store.py` (待创建)**:
    *   功能：遍历指定案例类型 `cases/` 目录下的所有 `.txt` 文件，读取内容，使用 `sentence-transformers` 进行向量化，并将文本、向量和元数据（文件名、案件类型）存储到对应类型的ChromaDB集合中。
*   **`app.py` (待创建)**:
    *   功能：Flask Web应用程序的入口，包含前端路由、后端API接口（接收查询、与ChromaDB交互、返回结果）。

## 4. 数据存储结构 (预期)

```
.
├── 民事案例/
│   ├── all_cases.txt         (清理后的总文件)
│   └── cases/                (分割后的独立案例.txt文件)
│       ├── 案件A.txt
│       └── 案件B.txt
├── 刑事案例/
│   ├── all_cases.txt
│   └── cases/
├── 行政案例/
│   ├── all_cases.txt
│   └── cases/
├── 执行案例/
│   ├── all_cases.txt
│   └── cases/
├── 国家赔偿案例/
│   ├── all_cases.txt
│   └── cases/
├── 指导案/                   (特殊处理的指导案例)
│   └── ... (已清理并重命名的.txt文件)
├── db/                       (ChromaDB 持久化数据存储目录)
│   └── chroma.sqlite3        (ChromaDB默认的SQLite后端)
│   └── ...                   (其他ChromaDB索引文件)
├── venv/                     (Python虚拟环境)
├── .gitignore
├── requirements.txt
├── extract_cases.py
├── clean_single_all_cases_file.py
├── clean_guiding_cases.py
├── vectorize_and_store.py    (待创建)
├── app.py                    (待创建)
└── PROJECT_DOCUMENTATION.md  (本文档)
```

## 5. 工作流程概要

1.  **数据准备**：
    *   （已完成）将原始PDF转换为各大类的 `all_cases.txt`。
    *   （已完成）使用 `clean_single_all_cases_file.py` 清理每个 `all_cases.txt`。
    *   （已完成）使用 `extract_cases.py` 将清理后的 `all_cases.txt` 分割为独立的案例文件到相应的 `cases/` 目录。
    *   （已完成）针对 `指导案` 目录下的文件，使用 `clean_guiding_cases.py` 进行特殊清理和重命名。
2.  **知识库填充** (后续步骤)：
    *   运行 `vectorize_and_store.py` 脚本，为每个案例类型的 `cases/` 目录下的文件进行处理：
        *   指定案件类型。
        *   读取案例文件。
        *   向量化文本。
        *   存入该案件类型对应的ChromaDB集合。
3.  **用户查询** (后续步骤)：
    *   启动 `app.py` (Flask应用)。
    *   用户通过浏览器访问Web界面。
    *   用户选择案例类型，输入查询。
    *   系统返回相关案例列表。

## 6. 后续开发步骤

1.  **实现 `vectorize_and_store.py` 脚本**：
    *   参数化输入（如案件类型、案例文件目录路径、ChromaDB集合名称、ChromaDB持久化路径）。
    *   实现ChromaDB客户端初始化和集合创建/加载逻辑。
    *   实现文本读取、向量化和数据（包括元数据）存入ChromaDB的逻辑。
    *   为所有五种案例类型分别执行此脚本，填充各自的知识库。
2.  **实现 `app.py` Flask Web应用**：
    *   设计基本的前端HTML页面（查询框、下拉菜单、结果展示区）。
    *   创建Flask路由：
        *   `/`: 显示主查询页面。
        *   `/search` (POST):接收查询参数，与ChromaDB交互，渲染结果页面。
    *   实现查询向量化和ChromaDB检索逻辑。
3.  **测试与迭代**：
    *   对不同类型的查询进行测试，评估检索结果的相关性和准确性。
    *   根据测试结果调整向量化模型（如果需要）、ChromaDB查询参数或前端展示。 