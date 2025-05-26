"""
法院判例知识库 - 云端Flask应用
使用远程embedding API，适合低资源环境部署
"""

import logging
import gc
import psutil
import os
import re
from flask import Flask, render_template, request, jsonify
import chromadb
import requests
from pypinyin import pinyin, Style

# 导入云端配置和服务
from config_cloud import (
    CHROMA_DATA_PATH, COLLECTION_NAME_PREFIX, FLASK_HOST, FLASK_PORT, FLASK_DEBUG,
    LLM_API_URL, LLM_API_KEY, LLM_MODEL_NAME, ENABLE_MONITORING,
    validate_config, get_embedding_dimensions
)
from embedding_service import get_embedding_service

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("--- Cloud Flask app starting ---")

# 验证配置
try:
    validate_config()
    logger.info("Configuration validated successfully")
except Exception as e:
    logger.error(f"Configuration validation failed: {e}")
    exit(1)

app = Flask(__name__)
logger.info("--- Flask app initialized ---")

# LLM配置检查
LLM_ENABLED = all([LLM_API_URL, LLM_API_KEY, LLM_MODEL_NAME])
if not LLM_ENABLED:
    logger.warning("LLM configuration missing. LLM analysis will be disabled.")
else:
    logger.info("LLM configuration loaded successfully")

# 全局变量（延迟初始化）
client = None
embedding_service = None

def get_memory_usage():
    """获取当前内存使用情况"""
    if ENABLE_MONITORING:
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,  # 物理内存
            'vms_mb': memory_info.vms / 1024 / 1024,  # 虚拟内存
        }
    return None

def init_services():
    """初始化ChromaDB和embedding服务"""
    global client, embedding_service
    
    if client is None:
        logger.info("Initializing ChromaDB client...")
        try:
            client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
            logger.info("ChromaDB client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise
    
    if embedding_service is None:
        logger.info("Initializing embedding service...")
        try:
            embedding_service = get_embedding_service()
            logger.info("Embedding service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize embedding service: {e}")
            raise
    
    # 记录内存使用
    memory_info = get_memory_usage()
    if memory_info:
        logger.info(f"Memory usage after initialization: {memory_info['rss_mb']:.1f}MB RSS, {memory_info['vms_mb']:.1f}MB VMS")

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
    
    prompt = f"请对以下法院判例内容进行分析和总结，提取关键信息，例如案情摘要、争议焦点、裁判理由等。请用中文回答。案例内容：\\n\\n{case_document}"

    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": LLM_MODEL_NAME,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1024,
        "temperature": 0.7
    }

    try:
        response = requests.post(LLM_API_URL, headers=headers, json=data, timeout=90)
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
    return render_template('index.html')

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

    logger.info(f"Received document for LLM analysis (length: {len(case_document)})")
    
    # 记录分析前的内存使用
    memory_before = get_memory_usage()
    
    analysis_result = analyze_case_with_llm(case_document)
    
    # 记录分析后的内存使用
    memory_after = get_memory_usage()
    if memory_before and memory_after:
        memory_diff = memory_after['rss_mb'] - memory_before['rss_mb']
        logger.info(f"Memory usage change during LLM analysis: {memory_diff:+.1f}MB")
    
    # 检查是否为错误消息
    error_indicators = [
        "大模型分析未启用", "请求大模型超时", "请求大模型API失败", 
        "大模型返回了意外的响应结构", "处理大模型分析时发生未知错误"
    ]
    
    if any(err_msg in analysis_result for err_msg in error_indicators):
        return jsonify({"error": analysis_result}), 500
        
    return jsonify({"analysis": analysis_result})

@app.route('/search', methods=['POST'])
def search():
    """搜索API端点"""
    logger.info("Search route called")
    
    # 确保服务已初始化
    if client is None or embedding_service is None:
        logger.info("Initializing services for search request")
        try:
            init_services()
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            return jsonify({"error": f"服务初始化失败: {str(e)}"}), 500
        
    query_text = request.form.get('query')
    case_type_folder = request.form.get('case_type_folder')

    if not query_text or not case_type_folder:
        return jsonify({"error": "请提供查询语句和案件类型"}), 400

    collection_name = get_clean_collection_name(case_type_folder)
    
    # 记录搜索前的内存使用
    memory_before = get_memory_usage()
    
    results = []
    try:
        logger.info(f"Searching in collection: {collection_name} for query: '{query_text}'")
        
        # 获取集合（使用云端embedding函数）
        from vectorize_and_store_cloud import CloudEmbeddingFunction
        ef = CloudEmbeddingFunction()
        
        collection = client.get_collection(name=collection_name, embedding_function=ef)
        
        # 执行查询
        query_results = collection.query(
            query_texts=[query_text],
            n_results=1,
            include=["metadatas", "documents"]
        )
        
        if query_results and query_results.get("ids") and query_results.get("ids")[0]:
            for i in range(len(query_results["ids"][0])):
                case_document_text = query_results["documents"][0][i]
                result_item = {
                    "id": query_results["ids"][0][i],
                    "filename": query_results["metadatas"][0][i].get("filename", "N/A"),
                    "document": case_document_text,
                }
                results.append(result_item)
                
            logger.info(f"Found {len(results)} results for query")
        else:
            logger.info(f"No results found for query '{query_text}' in '{collection_name}'")
            
    except Exception as e:
        error_message = f"搜索过程中发生错误: {str(e)}"
        logger.error(error_message)
        
        if "does not exist" in str(e).lower() or "not found" in str(e).lower():
            error_message = f"错误：知识库集合 '{collection_name}' 不存在。请确保您已运行向量化脚本为 '{case_type_folder}' 创建了知识库。"
        
        return jsonify({"error": error_message, "debug_collection_name": collection_name}), 500
    
    finally:
        # 强制垃圾回收以释放内存
        gc.collect()
        
        # 记录搜索后的内存使用
        memory_after = get_memory_usage()
        if memory_before and memory_after:
            memory_diff = memory_after['rss_mb'] - memory_before['rss_mb']
            logger.info(f"Memory usage change during search: {memory_diff:+.1f}MB")

    return jsonify({"results": results, "debug_collection_name": collection_name})

@app.route('/health')
def health_check():
    """健康检查端点"""
    try:
        memory_info = get_memory_usage()
        
        # 检查服务状态
        services_status = {
            "chromadb": client is not None,
            "embedding_service": embedding_service is not None,
            "llm_enabled": LLM_ENABLED
        }
        
        response = {
            "status": "healthy",
            "services": services_status,
            "memory": memory_info
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500

if __name__ == '__main__':
    logger.info("Starting cloud Flask application...")
    
    # 预初始化服务（可选）
    try:
        init_services()
        logger.info("Services pre-initialized successfully")
    except Exception as e:
        logger.warning(f"Service pre-initialization failed: {e}")
        logger.info("Services will be initialized on first request")
    
    # 启动应用
    logger.info(f"Starting Flask app on {FLASK_HOST}:{FLASK_PORT}")
    app.run(
        host=FLASK_HOST,
        port=FLASK_PORT,
        debug=FLASK_DEBUG,
        threaded=True  # 启用多线程支持
    ) 