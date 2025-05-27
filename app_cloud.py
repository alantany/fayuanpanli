"""
法院判例知识库 - 云端Flask应用（查询专用版）
仅提供向量数据库查询服务，不包含embedding功能
适合1C2G低资源环境部署
"""

import logging
import os
import re
from flask import Flask, render_template, request, jsonify
import chromadb
import requests
from pypinyin import pinyin, Style
from chromadb.config import Settings

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("--- .env file loaded successfully ---")
except ImportError:
    print("--- python-dotenv not installed, using system environment variables ---")
except Exception as e:
    print(f"--- Error loading .env file: {e} ---")

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("--- Cloud Query-Only Flask app starting ---")

app = Flask(__name__)
logger.info("--- Flask app initialized ---")

# 配置参数（简化版）
CHROMA_DATA_PATH = os.getenv("CHROMA_DATA_PATH", "db/")
COLLECTION_NAME_PREFIX = "knowledge_base_"
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")  # 云端通常需要绑定到0.0.0.0
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"

# LLM配置
LLM_API_URL = os.getenv("LLM_API_URL")
LLM_API_KEY = os.getenv("LLM_API_KEY") 
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME")

# Embedding API配置（新增）
EMBEDDING_API_URL = os.getenv("EMBEDDING_API_URL")  # 如：https://api.openai.com/v1/embeddings
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY")  # 可以与LLM_API_KEY相同
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "text-embedding-ada-002")  # OpenAI默认模型

# LLM配置检查
LLM_ENABLED = all([LLM_API_URL, LLM_API_KEY, LLM_MODEL_NAME])
if not LLM_ENABLED:
    logger.warning("LLM configuration missing. LLM analysis will be disabled.")
else:
    logger.info("LLM configuration loaded successfully")

# Embedding配置检查
EMBEDDING_API_ENABLED = all([EMBEDDING_API_URL, EMBEDDING_API_KEY])
if not EMBEDDING_API_ENABLED:
    logger.warning("Embedding API configuration missing. Will use ChromaDB default embedding.")
else:
    logger.info("Embedding API configuration loaded successfully")

# 全局变量
client = None

# 案例类型映射（与主应用保持一致）
CASE_TYPES = {
    "民事案例": "民事案例",
    "刑事案例": "刑事案例", 
    "行政案例": "行政案例",
    "执行案例": "执行案例",
    "国家赔偿案例": "国家赔偿案例"
}

# 添加embedding支持
FORCE_DISABLE_EMBEDDING = os.getenv("FORCE_DISABLE_EMBEDDING", "False").lower() == "true"

if FORCE_DISABLE_EMBEDDING:
    EMBEDDING_AVAILABLE = False
    print("Embedding disabled by environment variable")
else:
    try:
        from sentence_transformers import SentenceTransformer
        EMBEDDING_AVAILABLE = True
    except ImportError:
        EMBEDDING_AVAILABLE = False
        print("Warning: sentence-transformers not available, using ChromaDB default embedding")

def init_chromadb():
    """初始化ChromaDB客户端"""
    global client
    
    try:
        # 初始化ChromaDB客户端
        client = chromadb.PersistentClient(path="./db")
        logger.info("ChromaDB client initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize ChromaDB: {e}")
        raise

def get_clean_collection_name(case_type_folder_name_raw):
    """生成清理过的集合名称（与向量化脚本保持一致）"""
    pinyin_list = pinyin(case_type_folder_name_raw, style=Style.NORMAL)
    cleaned_name = "_".join([item[0] for item in pinyin_list if item[0]])
    
    cleaned_name = cleaned_name.lower()
    cleaned_name = re.sub(r'[^a-z0-9_]', '', cleaned_name)
    cleaned_name = cleaned_name.replace('-', '_')
    cleaned_name = re.sub(r'_+', '_', cleaned_name)
    cleaned_name = cleaned_name.strip('_')

    if not cleaned_name:
        cleaned_name = "default_topic"

    prefix_len = len(COLLECTION_NAME_PREFIX)
    max_name_len = 63 - prefix_len
    
    if len(cleaned_name) > max_name_len:
        cleaned_name = cleaned_name[:max_name_len]
    
    cleaned_name = cleaned_name.strip('_')
    
    if not cleaned_name or len(cleaned_name) < 1:
        cleaned_name = "fallback"

    full_collection_name = f"{COLLECTION_NAME_PREFIX}{cleaned_name}"
    
    # 简化的安全检查
    if not cleaned_name.replace('_', '').isalnum():
        safe_name = ''.join(c for c in cleaned_name if c.isalnum() or c == '_')
        if not safe_name:
            safe_name = "safe"
        full_collection_name = f"{COLLECTION_NAME_PREFIX}{safe_name}"
    
    return full_collection_name

def analyze_case_with_llm(case_document):
    """使用LLM分析案例"""
    if not LLM_ENABLED:
        logger.warning("LLM analysis disabled due to missing configuration")
        return "大模型分析未启用或配置不正确。"

    logger.info(f"Sending case to LLM for analysis (length: {len(case_document)} chars)")
    
    prompt = f"""请对以下法院判例内容进行分析和总结，提取关键信息。请按以下格式输出：

### 案情摘要
[简要概述案件基本情况]

### 争议焦点
[列出主要争议点]

### 裁判理由
[法院的主要裁判依据和理由]

### 法律适用
[适用的主要法律条文]

### 判决结果分析
[对判决结果的分析]

### 案件启示
[案件的法律意义和启示]

案例内容：

{case_document}"""

    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": LLM_MODEL_NAME,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1500,
        "temperature": 0.3
    }

    try:
        response = requests.post(LLM_API_URL, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        
        llm_response_data = response.json()
        
        if llm_response_data.get("choices") and llm_response_data["choices"][0].get("message"):
            analysis = llm_response_data["choices"][0]["message"].get("content", "").strip()
            logger.info("LLM analysis completed successfully")
            return analysis if analysis else "大模型返回了空的分析结果。"
        else:
            error_detail = llm_response_data.get("error", {}).get("message", "未知错误结构")
            logger.error(f"LLM API returned unexpected structure: {error_detail}")
            return f"大模型返回了意外的响应结构: {error_detail}"

    except requests.exceptions.Timeout:
        logger.error("LLM API request timed out")
        return "请求大模型超时。"
    except requests.exceptions.HTTPError as http_err:
        error_content = "未知错误"
        try:
            error_content = response.json().get("error", {}).get("message", str(http_err))
        except:
            error_content = str(http_err)
        logger.error(f"LLM API HTTP error: {error_content}")
        return f"请求大模型API失败: {error_content}"
    except requests.exceptions.RequestException as e:
        logger.error(f"LLM API request failed: {str(e)}")
        return f"请求大模型时发生网络错误: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error during LLM analysis: {str(e)}")
        return f"处理大模型分析时发生未知错误: {str(e)}"

def get_embedding_from_api(text):
    """使用云端API获取文本的embedding向量"""
    if not EMBEDDING_API_ENABLED:
        return None
        
    headers = {
        "Authorization": f"Bearer {EMBEDDING_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": EMBEDDING_MODEL_NAME,
        "input": text
    }
    
    try:
        response = requests.post(EMBEDDING_API_URL, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        if 'data' in result and len(result['data']) > 0:
            embedding = result['data'][0]['embedding']
            logger.info(f"Successfully got embedding from API (dimension: {len(embedding)})")
            return embedding
        else:
            logger.error("Invalid response format from embedding API")
            return None
            
    except requests.exceptions.Timeout:
        logger.error("Embedding API request timed out")
        return None
    except requests.exceptions.HTTPError as e:
        logger.error(f"Embedding API HTTP error: {e}")
        return None
    except Exception as e:
        logger.error(f"Error calling embedding API: {e}")
        return None

@app.route('/')
def index():
    """主页"""
    return render_template('index.html', case_types=CASE_TYPES)

@app.route('/analyze_case_llm', methods=['POST'])
def analyze_case_llm_route():
    """LLM分析API端点"""
    logger.info("LLM analysis route called")
    
    if not LLM_ENABLED:
        return jsonify({"error": "LLM analysis is disabled."}), 403

    data = request.get_json()
    case_document = data.get('case_document')

    if not case_document:
        return jsonify({"error": "Missing case_document in request."}), 400

    try:
        analysis_result = analyze_case_with_llm(case_document)
        return jsonify({"analysis": analysis_result})
    except Exception as e:
        logger.error(f"Error in LLM analysis route: {str(e)}")
        return jsonify({"error": f"分析失败: {str(e)}"}), 500

@app.route('/search', methods=['POST'])
def search():
    """搜索API端点 - 支持向量搜索和关键词搜索"""
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': '请提供搜索查询'}), 400
        
        query = data['query']
        case_type = data.get('case_type', '')
        
        logger.info(f"搜索请求: query='{query}', case_type='{case_type}'")
        
        # 获取对应的集合
        collection_name = get_clean_collection_name(case_type) if case_type else None
        
        # 尝试连接数据库
        try:
            client = chromadb.PersistentClient(path="./db")
            
            if collection_name:
                try:
                    collection = client.get_collection(name=collection_name)
                    logger.info(f"Found specific collection: {collection_name}")
                except:
                    logger.warning(f"Collection {collection_name} not found, searching all collections")
                    collection = None
            else:
                collection = None
                
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return jsonify({'error': '数据库连接失败'}), 500
        
        # 执行搜索
        all_results = []
        
        if collection:
            # 搜索特定集合
            results = search_in_collection(collection, query)
            all_results.extend(results)
        else:
            # 搜索所有集合
            try:
                collections = client.list_collections()
                logger.info(f"Searching across {len(collections)} collections")
                
                for collection_info in collections:
                    try:
                        coll = client.get_collection(name=collection_info.name)
                        results = search_in_collection(coll, query)
                        all_results.extend(results)
                    except Exception as e:
                        logger.warning(f"Error searching collection {collection_info.name}: {e}")
                        continue
            except Exception as e:
                logger.error(f"Error listing collections: {e}")
                return jsonify({'error': '搜索失败'}), 500
        
        # 按相关性排序（距离越小越相关）
        all_results.sort(key=lambda x: x.get('distance', float('inf')))
        
        # 取最相关的结果
        formatted_results = all_results[:1] if all_results else []
        
        logger.info(f"Found {len(formatted_results)} results")
        return jsonify({'results': formatted_results})
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        return jsonify({'error': '搜索过程中发生错误'}), 500

def search_in_collection(collection, query):
    """在指定集合中搜索"""
    results = []
    
    try:
        # 方法1: 尝试向量搜索（如果embedding API可用）
        if EMBEDDING_API_ENABLED:
            try:
                logger.info("Attempting vector search with cloud embedding API")
                query_embedding = get_embedding_from_api(query)
                if query_embedding is not None:
                    search_results = collection.query(
                        query_embeddings=[query_embedding],
                        n_results=5,
                        include=["documents", "metadatas", "distances"]
                    )
                    
                    if search_results['documents'] and search_results['documents'][0]:
                        for i, doc in enumerate(search_results['documents'][0]):
                            metadata = search_results['metadatas'][0][i] if search_results['metadatas'][0] else {}
                            distance = search_results['distances'][0][i] if search_results['distances'][0] else 0
                            
                            results.append({
                                'filename': metadata.get('filename', f'案例_{i+1}.txt'),
                                'document': doc,
                                'distance': distance,
                                'case_type': metadata.get('case_type', '未知类型'),
                                'search_method': 'vector_api'
                            })
                        return results
            except Exception as e:
                logger.warning(f"Vector search failed: {e}")
        
        # 方法2: 尝试ChromaDB默认向量搜索
        try:
            logger.info("Attempting ChromaDB default vector search")
            search_results = collection.query(
                query_texts=[query],
                n_results=5,
                include=["documents", "metadatas", "distances"]
            )
            
            if search_results['documents'] and search_results['documents'][0]:
                for i, doc in enumerate(search_results['documents'][0]):
                    metadata = search_results['metadatas'][0][i] if search_results['metadatas'][0] else {}
                    distance = search_results['distances'][0][i] if search_results['distances'][0] else 0
                    
                    results.append({
                        'filename': metadata.get('filename', f'案例_{i+1}.txt'),
                        'document': doc,
                        'distance': distance,
                        'case_type': metadata.get('case_type', '未知类型'),
                        'search_method': 'vector_default'
                    })
                return results
        except Exception as e:
            logger.warning(f"Default vector search failed: {e}")
        
        # 方法3: 关键词搜索（最可靠的备选方案）
        logger.info("Falling back to keyword search")
        return keyword_search_in_collection(collection, query)
        
    except Exception as e:
        logger.error(f"All search methods failed in collection: {e}")
        return []

def keyword_search_in_collection(collection, query):
    """在集合中进行关键词搜索"""
    results = []
    
    try:
        # 获取所有文档和元数据
        all_data = collection.get(include=["documents", "metadatas"])
        
        if not all_data['documents']:
            return results
        
        # 提取搜索关键词
        keywords = extract_keywords(query)
        logger.info(f"Extracted keywords: {keywords}")
        
        # 对每个文档计算相关性分数
        scored_docs = []
        for i, doc in enumerate(all_data['documents']):
            metadata = all_data['metadatas'][i] if i < len(all_data['metadatas']) else {}
            
            # 计算关键词匹配分数
            score = calculate_keyword_score(doc, metadata, keywords, query)
            
            if score > 0:  # 只保留有匹配的文档
                scored_docs.append({
                    'document': doc,
                    'metadata': metadata,
                    'score': score,
                    'distance': 1.0 - score  # 转换为距离（越小越相关）
                })
        
        # 按分数排序
        scored_docs.sort(key=lambda x: x['score'], reverse=True)
        
        # 返回最相关的结果
        for doc_info in scored_docs[:5]:
            results.append({
                'filename': doc_info['metadata'].get('filename', '未知文件.txt'),
                'document': doc_info['document'],
                'distance': doc_info['distance'],
                'case_type': doc_info['metadata'].get('case_type', '未知类型'),
                'search_method': 'keyword',
                'keyword_score': doc_info['score']
            })
        
        logger.info(f"Keyword search found {len(results)} relevant documents")
        return results
        
    except Exception as e:
        logger.error(f"Keyword search failed: {e}")
        return []

def extract_keywords(query):
    """从查询中提取关键词"""
    import re
    
    # 移除标点符号，分割成词
    clean_query = re.sub(r'[^\w\s]', ' ', query)
    words = clean_query.split()
    
    # 定义常见的法律关键词
    legal_keywords = {
        '婚姻': ['婚姻', '离婚', '夫妻', '配偶', '结婚'],
        '合同': ['合同', '协议', '约定', '违约'],
        '交通': ['交通', '车祸', '事故', '撞车', '肇事'],
        '劳动': ['劳动', '工作', '雇佣', '员工', '工资'],
        '房产': ['房产', '房屋', '买卖', '租赁', '物业'],
        '刑事': ['刑事', '犯罪', '盗窃', '诈骗', '故意'],
        '民事': ['民事', '纠纷', '争议', '赔偿'],
        '行政': ['行政', '政府', '行政机关', '执法'],
        '执行': ['执行', '强制执行', '申请执行'],
        '国家赔偿': ['国家赔偿', '赔偿', '国家机关']
    }
    
    # 扩展关键词
    expanded_keywords = set(words)
    for word in words:
        for category, synonyms in legal_keywords.items():
            if word in synonyms:
                expanded_keywords.update(synonyms)
    
    return list(expanded_keywords)

def calculate_keyword_score(document, metadata, keywords, original_query):
    """计算文档的关键词匹配分数"""
    score = 0.0
    
    # 将文档和元数据转换为小写用于匹配
    doc_lower = document.lower()
    filename_lower = metadata.get('filename', '').lower()
    case_type_lower = metadata.get('case_type', '').lower()
    
    # 原始查询的完整匹配（最高权重）
    if original_query.lower() in doc_lower:
        score += 10.0
    
    # 文件名匹配（高权重）
    for keyword in keywords:
        if keyword.lower() in filename_lower:
            score += 5.0
    
    # 案例类型匹配（中等权重）
    for keyword in keywords:
        if keyword.lower() in case_type_lower:
            score += 3.0
    
    # 文档内容匹配（基础权重）
    for keyword in keywords:
        count = doc_lower.count(keyword.lower())
        score += count * 1.0
    
    # 标准化分数（0-1之间）
    max_possible_score = 10.0 + len(keywords) * 6.0  # 估算最大可能分数
    normalized_score = min(score / max_possible_score, 1.0) if max_possible_score > 0 else 0.0
    
    return normalized_score

@app.route('/health')
def health_check():
    """健康检查端点"""
    try:
        if client is None:
            init_chromadb()
        
        collections = client.list_collections()
        
        return jsonify({
            "status": "healthy",
            "collections_count": len(collections),
            "available_collections": [c.name for c in collections],
            "llm_enabled": LLM_ENABLED
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy", 
            "error": str(e)
        }), 500

if __name__ == '__main__':
    logger.info(f"Starting Flask app on {FLASK_HOST}:{FLASK_PORT}")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG) 