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

# LLM配置检查
LLM_ENABLED = all([LLM_API_URL, LLM_API_KEY, LLM_MODEL_NAME])
if not LLM_ENABLED:
    logger.warning("LLM configuration missing. LLM analysis will be disabled.")
else:
    logger.info("LLM configuration loaded successfully")

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

def init_chromadb():
    """初始化ChromaDB客户端"""
    global client
    
    if client is None:
        logger.info("Initializing ChromaDB client...")
        try:
            client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
            logger.info("ChromaDB client initialized successfully")
            
            # 列出可用的集合
            collections = client.list_collections()
            logger.info(f"Available collections: {[c.name for c in collections]}")
            
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
    """搜索API端点 - 使用预存储的向量进行查询"""
    query = request.form.get('query', '').strip()
    case_type_folder = request.form.get('case_type_folder', '民事案例')
    
    logger.info(f"Search request: query='{query}', case_type='{case_type_folder}'")
    
    if not query:
        return jsonify({"error": "查询内容不能为空"}), 400
    
    # 初始化ChromaDB（如果尚未初始化）
    if client is None:
        try:
            init_chromadb()
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            return jsonify({"error": f"数据库初始化失败: {str(e)}"}), 500
    
    try:
        # 获取集合名称
        collection_name = get_clean_collection_name(case_type_folder)
        logger.info(f"Attempting to access collection: {collection_name}")
        
        # 获取集合
        try:
            collection = client.get_collection(name=collection_name)
        except Exception as e:
            logger.error(f"Collection not found: {collection_name}")
            return jsonify({
                "error": f"未找到 '{case_type_folder}' 类型的案例数据",
                "debug_collection_name": collection_name,
                "results": []
            }), 404
        
        # 注意：这里我们直接使用查询文本，依赖ChromaDB的内置embedding
        # 因为数据是用相同embedding模型存储的，查询时ChromaDB会自动处理
        results = collection.query(
            query_texts=[query],
            n_results=1,
            include=["documents", "metadatas", "distances"]
        )
        
        # 处理搜索结果
        formatted_results = []
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                metadata = results['metadatas'][0][i] if results['metadatas'][0] else {}
                distance = results['distances'][0][i] if results['distances'][0] else 0
                
                filename = metadata.get('filename', f'案例_{i+1}.txt')
                
                formatted_results.append({
                    'filename': filename,
                    'document': doc,
                    'distance': distance
                })
        
        logger.info(f"Found {len(formatted_results)} results")
        
        return jsonify({
            "results": formatted_results,
            "debug_collection_name": collection_name
        })
        
    except Exception as e:
        logger.error(f"Error during search: {str(e)}")
        return jsonify({
            "error": f"搜索过程中发生错误: {str(e)}",
            "debug_collection_name": collection_name if 'collection_name' in locals() else "unknown"
        }), 500

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