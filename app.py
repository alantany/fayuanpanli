print("--- app.py script started ---")

from flask import Flask, render_template, request, jsonify
import chromadb
from chromadb.utils import embedding_functions
import os
import re
from pypinyin import pinyin, Style
import requests # Added for LLM calls
from dotenv import load_dotenv # Added to load .env file

print("--- Imports completed ---")

load_dotenv() # Load environment variables from .env file
print("--- .env file loaded ---")

app = Flask(__name__)
print("--- Flask app initialized ---")

# --- LLM Configuration ---
LLM_API_URL = os.getenv("LLM_API_URL")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME")

if not all([LLM_API_URL, LLM_API_KEY, LLM_MODEL_NAME]):
    print("!!! WARNING: LLM configuration (API URL, Key, or Model Name) is missing from .env file. LLM analysis will be disabled. !!!")
    LLM_ENABLED = False
else:
    LLM_ENABLED = True
    print("--- LLM Configuration loaded successfully ---")


# --- 从 vectorize_and_store.py 复制过来的配置和函数 ---
CHROMA_DATA_PATH = "db/"
SENTENCE_TRANSFORMER_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
COLLECTION_NAME_PREFIX = "knowledge_base_"

# 确保ChromaDB数据目录存在 (虽然主要由vectorize脚本创建)
os.makedirs(CHROMA_DATA_PATH, exist_ok=True)
print(f"--- CHROMA_DATA_PATH checked/created: {os.path.abspath(CHROMA_DATA_PATH)} ---")

# 全局ChromaDB客户端和嵌入函数 (延迟初始化)
client = None
ef = None

def init_chroma():
    print("--- Attempting to initialize ChromaDB (init_chroma called) ---")
    global client, ef
    if client is None:
        print(f"Initializing ChromaDB client for web app with persistence to: {os.path.abspath(CHROMA_DATA_PATH)}")
        client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
        print("--- ChromaDB client potentially initialized ---")
    if ef is None:
        print(f"Initializing embedding function for web app with model: {SENTENCE_TRANSFORMER_MODEL}")
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=SENTENCE_TRANSFORMER_MODEL
        )
        print("--- Embedding function potentially initialized ---")
    print("--- ChromaDB client and embedding function are ready for web app (init_chroma finished) ---")

def get_clean_collection_name(case_type_folder_name_raw):
    """根据案件类型的文件夹名生成一个清理过的、适合做集合名的字符串。"""
    pinyin_list = pinyin(case_type_folder_name_raw, style=Style.NORMAL)
    cleaned_name = "_".join([item[0] for item in pinyin_list if item[0]])
    cleaned_name = cleaned_name.lower()
    cleaned_name = re.sub(r'[^a-z0-9_]', '', cleaned_name)
    cleaned_name = cleaned_name.replace('-', '_')
    cleaned_name = re.sub(r'_+', '_', cleaned_name)
    cleaned_name = cleaned_name.strip('_')

    if not cleaned_name:
        # Simplified fallback for web app context
        cleaned_name = f"default_collection_{hash(case_type_folder_name_raw)}" 

    prefix_len = len(COLLECTION_NAME_PREFIX)
    max_name_len = 63 - prefix_len
    cleaned_name = cleaned_name[:max_name_len]
    cleaned_name = cleaned_name.strip('_')

    if not cleaned_name or len(cleaned_name) < 1:
        cleaned_name = f"fallback_{hash(case_type_folder_name_raw)}"

    full_collection_name = f"{COLLECTION_NAME_PREFIX}{cleaned_name}"
    
    # Basic check, can be enhanced if needed
    if not re.match(r"^[a-z0-9][a-z0-9_.-]{1,61}[a-z0-9]$", full_collection_name):
        # Fallback for very problematic names, ensuring some operation
        temp_name = re.sub(r'[^a-z0-9_]', '', cleaned_name)
        full_collection_name = f"{COLLECTION_NAME_PREFIX}{temp_name[:max_name_len]}"
        if not full_collection_name[len(COLLECTION_NAME_PREFIX):]: # check if name part is empty
             full_collection_name = f"{COLLECTION_NAME_PREFIX}emergency_fallback"
        full_collection_name = full_collection_name[:63] # final trim
        # Ensure it starts and ends with alphanumeric, crudely if necessary
        if not full_collection_name[len(COLLECTION_NAME_PREFIX):].isalnum(): # check name part
            full_collection_name = COLLECTION_NAME_PREFIX + "c" + full_collection_name[len(COLLECTION_NAME_PREFIX):]
        if not full_collection_name[-1].isalnum():
             full_collection_name = full_collection_name[:-1] + "e"
        full_collection_name = full_collection_name[:63]


    return full_collection_name

def analyze_case_with_llm(case_document):
    """
    Sends the case document to the LLM for analysis and returns the analysis.
    """
    if not LLM_ENABLED:
        print("LLM analysis is disabled due to missing configuration.")
        return "大模型分析未启用或配置不正确。"

    print(f"--- Sending to LLM for analysis. Document starts with: {case_document[:200]}... ---")
    
    # Basic prompt, can be significantly improved with prompt engineering
    # For Chinese text, it's good practice to be explicit if the model expects it.
    # The DeepSeek model used is multilingual and good with Chinese.
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
        "max_tokens": 1024, # Adjust as needed
        "temperature": 0.7   # Adjust for creativity vs. factuality
    }

    try:
        response = requests.post(LLM_API_URL, headers=headers, json=data, timeout=90) # Increased timeout
        response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
        
        llm_response_data = response.json()
        
        # --- Log the raw LLM response for debugging ---
        # print(f"LLM Raw Response: {llm_response_data}") 
        # ---

        if llm_response_data.get("choices") and llm_response_data["choices"][0].get("message"):
            analysis = llm_response_data["choices"][0]["message"].get("content", "").strip()
            print("--- LLM analysis received successfully. ---")
            return analysis if analysis else "大模型返回了空的分析结果。"
        else:
            error_detail = llm_response_data.get("error", {}).get("message", "未知错误结构")
            print(f"LLM API returned unexpected structure or no content: {error_detail}")
            # print(f"Full LLM response for debugging unexpected structure: {llm_response_data}")
            return f"大模型返回了意外的响应结构: {error_detail}"

    except requests.exceptions.Timeout:
        print("LLM API request timed out.")
        return "请求大模型超时。"
    except requests.exceptions.HTTPError as http_err:
        error_content = "未知错误"
        try:
            error_content = response.json().get("error", {}).get("message", str(http_err))
        except: # In case response is not JSON or structure is different
            error_content = str(http_err)
        print(f"LLM API request failed with HTTPError: {error_content}")
        return f"请求大模型API失败: {error_content}"
    except requests.exceptions.RequestException as e:
        print(f"LLM API request failed: {str(e)}")
        return f"请求大模型时发生网络错误: {str(e)}"
    except Exception as e:
        print(f"An unexpected error occurred during LLM analysis: {str(e)}")
        return f"处理大模型分析时发生未知错误: {str(e)}"


# --- 应用特定的配置 ---
# 定义我们目前支持的案件类型 (显示名称, 用于生成集合名的文件夹名)
AVAILABLE_CASE_TYPES = {
    "国家赔偿案例": "国家赔偿案例",
    "民事案例": "民事案例", 
    "刑事案例": "刑事案例",
    "行政案例": "行政案例",
    "执行案例": "执行案例",
}
print("--- AVAILABLE_CASE_TYPES defined ---")

@app.route('/')
def index():
    print("--- Route / called ---")
    # 在第一次请求时初始化ChromaDB
    # 修改：如果应用启动时已经初始化，这里可能不需要再次检查，
    # 但保留它可以作为一种保障，或改为在 __main__ 中只调用一次。
    # 当前设计是在 __main__ 中调用，也在第一次请求时检查。
    if client is None or ef is None:
        print("--- init_chroma() called from index route ---")
        init_chroma()
    return render_template('index.html', case_types=AVAILABLE_CASE_TYPES)

@app.route('/analyze_case_llm', methods=['POST'])
def analyze_case_llm_route():
    print("--- Route /analyze_case_llm called ---")
    if not LLM_ENABLED:
        return jsonify({"error": "LLM analysis is disabled."}), 403 # Forbidden

    data = request.get_json()
    case_document = data.get('case_document')

    if not case_document:
        return jsonify({"error": "Missing case_document in request."}), 400

    print(f"--- Received document for LLM analysis. Length: {len(case_document)} ---")
    analysis_result = analyze_case_with_llm(case_document)
    
    # Check if the result indicates an error from analyze_case_with_llm
    if any(err_msg in analysis_result for err_msg in ["大模型分析未启用", "请求大模型超时", "请求大模型API失败", "大模型返回了意外的响应结构", "处理大模型分析时发生未知错误"]):
        # If it's an error message we constructed, return it with a 500 or appropriate status
        # This helps differentiate actual LLM content from our error messages.
        # However, the current analyze_case_with_llm returns strings directly. 
        # For a more robust API, it should ideally return a structured error or success response.
        # For now, we assume if it's one of these known error strings, it's an internal/API error.
        return jsonify({"error": analysis_result}), 500 
        
    return jsonify({"analysis": analysis_result})

@app.route('/search', methods=['POST'])
def search():
    print("--- Route /search called ---")
    if client is None or ef is None: # 确保初始化
        print("--- init_chroma() called from search route ---")
        init_chroma()
        
    query_text = request.form.get('query')
    case_type_folder = request.form.get('case_type_folder') # 这是文件夹名

    if not query_text or not case_type_folder:
        return jsonify({"error": "请提供查询语句和案件类型"}), 400

    collection_name = get_clean_collection_name(case_type_folder)
    
    results = [] # Changed back to just results, LLM analysis will be fetched on demand
    try:
        print(f"Searching in collection: {collection_name} for query: '{query_text}'")
        collection = client.get_collection(name=collection_name, embedding_function=ef) 
        
        query_results = collection.query(
            query_texts=[query_text],
            n_results=1, 
            include=["metadatas", "documents"] 
        )
        
        if query_results and query_results.get("ids") and query_results.get("ids")[0]:
            for i in range(len(query_results["ids"][0])):
                case_document_text = query_results["documents"][0][i]
                # LLM analysis is no longer done here directly
                result_item = {
                    "id": query_results["ids"][0][i],
                    "filename": query_results["metadatas"][0][i].get("filename", "N/A"),
                    "document": case_document_text,
                    # "llm_analysis": llm_analysis_text # Removed from initial response
                }
                results.append(result_item)
        else:
            print(f"No results found or unexpected result format for query '{query_text}' in '{collection_name}'.")
            
    except Exception as e:
        error_message = f"搜索过程中发生错误: {str(e)}"
        print(error_message)
        if "does not exist" in str(e).lower() or "not found" in str(e).lower():
             error_message = f"错误：知识库集合 '{collection_name}' 不存在。请确保您已运行 vectorize_and_store.py 脚本为 '{case_type_folder}' 创建了知识库。"
        return jsonify({"error": error_message, "debug_collection_name": collection_name}), 500

    return jsonify({"results": results, "debug_collection_name": collection_name}) # Return results without LLM analysis

if __name__ == '__main__':
    print("--- Entered __main__ block ---")
    print("--- Calling init_chroma() from __main__ ---")
    init_chroma() # 应用启动时预先初始化
    print("--- init_chroma() finished in __main__ ---")
    print("--- Attempting to start Flask app (app.run) ---")
    app.run(debug=True, port=5001) # 使用一个非默认端口避免冲突
    print("--- Flask app.run finished (should not see this if server is running) ---")

print("--- app.py script finished ---") 