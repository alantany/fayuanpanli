print("--- app.py script started ---")

from flask import Flask, render_template, request, jsonify
import chromadb
from chromadb.utils import embedding_functions
import os
import re
from pypinyin import pinyin, Style

print("--- Imports completed ---")

app = Flask(__name__)
print("--- Flask app initialized ---")

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
    
    results = []
    try:
        print(f"Searching in collection: {collection_name} for query: '{query_text}'")
        collection = client.get_collection(name=collection_name, embedding_function=ef) # Pass ef here
        
        query_results = collection.query(
            query_texts=[query_text],
            n_results=1, # 返回最相关的5个结果
            include=["metadatas", "documents"] # 包含元数据和文档内容
        )
        
        #  query_results 结构示例 (根据ChromaDB版本可能略有不同):
        # {
        #     "ids": [["id1", "id2"]],
        #     "distances": [[0.1, 0.2]],
        #     "metadatas": [[{"filename": "file1.txt", "case_type": "..." }, {"filename": "file2.txt", ...}]],
        #     "documents": [["doc content 1", "doc content 2"]],
        #     "uris": None,
        #     "data": None,
        # }
        # 我们只查询了一个文本，所以主要取第一个列表的元素

        if query_results and query_results.get("ids") and query_results.get("ids")[0]:
            for i in range(len(query_results["ids"][0])):
                result_item = {
                    "id": query_results["ids"][0][i],
                    "filename": query_results["metadatas"][0][i].get("filename", "N/A"),
                    "document": query_results["documents"][0][i],
                    # "distance": query_results["distances"][0][i] # 可以选择性显示
                }
                results.append(result_item)
        else:
            print(f"No results found or unexpected result format for query '{query_text}' in '{collection_name}'.")
            
    except Exception as e:
        error_message = f"搜索过程中发生错误: {str(e)}"
        print(error_message)
        # 检查是否是集合不存在的特定错误
        if "does not exist" in str(e).lower() or "not found" in str(e).lower():
             error_message = f"错误：知识库集合 '{collection_name}' 不存在。请确保您已运行 vectorize_and_store.py 脚本为 '{case_type_folder}' 创建了知识库。"
        return jsonify({"error": error_message, "debug_collection_name": collection_name}), 500

    return jsonify({"results": results, "debug_collection_name": collection_name})

if __name__ == '__main__':
    print("--- Entered __main__ block ---")
    print("--- Calling init_chroma() from __main__ ---")
    init_chroma() # 应用启动时预先初始化
    print("--- init_chroma() finished in __main__ ---")
    print("--- Attempting to start Flask app (app.run) ---")
    app.run(debug=True, port=5001) # 使用一个非默认端口避免冲突
    print("--- Flask app.run finished (should not see this if server is running) ---")

print("--- app.py script finished ---") 