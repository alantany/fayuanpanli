import chromadb
from chromadb.utils import embedding_functions
import os
import sys
import re
from tqdm import tqdm # 用于显示进度条
import time
from pypinyin import pinyin, Style # 新增导入

# --- 配置 ---
# ChromaDB 数据持久化路径
CHROMA_DATA_PATH = "db/"
# Sentence Transformer 模型，用于文本向量化
# paraphrase-multilingual-MiniLM-L12-v2 是一个对多种语言（包括中文）表现良好的模型
# 如果遇到网络问题无法下载，可以考虑换成国内镜像或者先下载到本地指定路径
SENTENCE_TRANSFORMER_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
# ChromaDB集合名称的前缀
COLLECTION_NAME_PREFIX = "knowledge_base_"
BATCH_SIZE = 50 # 每批处理和添加到ChromaDB的文档数量

# --- 初始化 ---
# 确保ChromaDB数据目录存在
os.makedirs(CHROMA_DATA_PATH, exist_ok=True)

print("Initializing embedding function...")
# ChromaDB >= 0.4.0, embedding_function is passed to get_or_create_collection
# For older versions, it might be passed to the client, but this is the modern way.
# We will pass it when creating/getting the collection.
print("Embedding function will be configured per collection using model:", SENTENCE_TRANSFORMER_MODEL)

print(f"Initializing ChromaDB client with persistence to: {os.path.abspath(CHROMA_DATA_PATH)}")
# 初始化ChromaDB客户端，使用PersistentClient以持久化数据
# 这会将数据存储在 CHROMA_DATA_PATH 指定的目录中
client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
print("ChromaDB client initialized.")

# --- 函数定义 ---
def get_clean_collection_name(case_type_folder_name_raw):
    """根据案件类型的文件夹名生成一个清理过的、适合做集合名的字符串。"""
    # 将中文文件夹名转换为拼音
    pinyin_list = pinyin(case_type_folder_name_raw, style=Style.NORMAL)
    cleaned_name = "_".join([item[0] for item in pinyin_list if item[0]])
    
    cleaned_name = cleaned_name.lower()
    # 移除非法字符，仅保留字母、数字、下划线
    cleaned_name = re.sub(r'[^a-z0-9_]', '', cleaned_name)
    # ChromaDB 集合名规则:
    # - 长度 3-63
    # - 以小写字母或数字开头和结尾
    # - 不能包含 .. (两个连续的点)
    # - 不能是 IP 地址格式
    # - 只能包含小写字母、数字、下划线_、点.、连字符- (我们这里主要生成下划线分隔)
    
    cleaned_name = cleaned_name.replace('-', '_') # 将连字符替换为下划线 (虽然pinyin转换后不太会有)
    cleaned_name = re.sub(r'_+', '_', cleaned_name) # 多个下划线变一个
    cleaned_name = cleaned_name.strip('_')

    if not cleaned_name:
        # 如果转换后为空 (例如输入是纯符号), 使用一个安全的回退名称
        timestamp_fallback = str(int(time.time()))[-6:] #取时间戳后6位避免太长
        cleaned_name = f"default_topic_{timestamp_fallback}"

    # 确保符合长度限制 (预留前缀长度)
    prefix_len = len(COLLECTION_NAME_PREFIX)
    max_name_len = 63 - prefix_len
    
    if len(cleaned_name) > max_name_len:
        cleaned_name = cleaned_name[:max_name_len]
    
    # 再次清理确保末尾不是下划线 (如果截断导致)
    cleaned_name = cleaned_name.strip('_')
    
    # 如果清理后还是空，或者太短，提供一个最终的简单回退
    if not cleaned_name or len(cleaned_name) < 1 : # 集合名本身至少1个字符
        timestamp_fallback = str(int(time.time()))[-6:]
        cleaned_name = f"fallback_{timestamp_fallback}"


    full_collection_name = f"{COLLECTION_NAME_PREFIX}{cleaned_name}"
    
    # 最终检查ChromaDB的完整命名规则
    # 长度3-63，开头结尾是字母数字，中间可以是字母数字、下划线、点、连字符
    # 我们生成的主要是小写字母、数字、下划线
    if not re.match(r"^[a-z0-9][a-z0-9_.-]{1,61}[a-z0-9]$", full_collection_name):
        # 尝试一个更安全的修复
        safe_name_parts = []
        for char in cleaned_name:
            if 'a' <= char <= 'z' or '0' <= char <= '9' or char == '_':
                safe_name_parts.append(char)
        
        safe_cleaned_name = "".join(safe_name_parts).strip('_')
        
        # 如果修复后太短或无效，使用最终回退
        if len(safe_cleaned_name) < 1:
            timestamp_fallback = str(int(time.time()))[-6:]
            safe_cleaned_name = f"gen_{timestamp_fallback}"

        safe_cleaned_name = safe_cleaned_name[:max_name_len] # 再次确保长度
        safe_cleaned_name = safe_cleaned_name.strip('_')
        
        # 确保开头结尾是字母或数字
        if not safe_cleaned_name or not safe_cleaned_name[0].isalnum():
            safe_cleaned_name = "c" + safe_cleaned_name # 加前缀'c'
        if not safe_cleaned_name[-1].isalnum():
            safe_cleaned_name = safe_cleaned_name + "e" # 加后缀'e'
            
        safe_cleaned_name = safe_cleaned_name[:max_name_len] # 再次确保长度
        
        full_collection_name = f"{COLLECTION_NAME_PREFIX}{safe_cleaned_name}"
        
        # 如果经过所有努力仍然不符合，这通常表示原始输入非常极端
        # 或者我们的前缀导致了问题
        if not re.match(r"^[a-z0-9][a-z0-9_.-]{1,61}[a-z0-9]$", full_collection_name):
            print(f"Critical Warning: Could not generate a compliant collection name for '{case_type_folder_name_raw}'. Generated '{full_collection_name}'. Using an emergency fallback.")
            full_collection_name = f"{COLLECTION_NAME_PREFIX}emergency_{str(int(time.time()))[-8:]}"
            full_collection_name = full_collection_name[:63].strip('_.-') # 确保符合长度和基本字符

    return full_collection_name

def process_and_store_cases(case_type_display_name, case_type_folder_name):
    """
    处理指定案件类型目录下的所有 .txt 文件，将其向量化并存入ChromaDB。
    
    Args:
        case_type_display_name (str): 用于元数据和日志的案件类型显示名称 (例如 "国家赔偿案例")。
        case_type_folder_name (str): 包含 'cases/' 子目录的案件类型的根目录名 (例如 "国家赔偿案例")。
                                     这个名称也用于生成集合名。
    """
    collection_name = get_clean_collection_name(case_type_folder_name)
    cases_dir = os.path.join(case_type_folder_name, "cases")
    
    print(f"\n--- Processing Case Type: {case_type_display_name} ---")
    print(f"Target collection: {collection_name}")
    print(f"Source directory: {os.path.abspath(cases_dir)}")

    if not os.path.isdir(cases_dir):
        print(f"Error: Cases directory not found: {cases_dir}")
        return

    filenames = [f for f in os.listdir(cases_dir) if f.endswith(".txt")]
    if not filenames:
        print(f"No .txt files found in {cases_dir}")
        return

    try:
        # 获取或创建集合。在首次创建时，ChromaDB会下载并初始化模型（如果需要）
        # Embedding function is specified here for ChromaDB version >= 0.4.0
        print(f"Getting or creating collection: {collection_name}...")
        start_time_ef = time.time()
        # 指定嵌入函数
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=SENTENCE_TRANSFORMER_MODEL,
            # device="cuda" # Uncomment for GPU
        )
        collection = client.get_or_create_collection(
            name=collection_name,
            embedding_function=ef
        )
        print(f"Collection obtained/created in {time.time() - start_time_ef:.2f} seconds.")

    except Exception as e:
        print(f"Error getting or creating collection {collection_name}: {e}")
        print("This might be due to an issue with the embedding model download or initialization.")
        print("Please check your internet connection and if the model name is correct.")
        print(f"Model used: {SENTENCE_TRANSFORMER_MODEL}")
        return

    documents_batch = []
    metadatas_batch = []
    ids_batch = []
    
    # Check for already processed files to avoid re-processing if script is run multiple times
    # This is a simple check; for very large datasets, a more robust checkpointing might be needed.
    try:
        existing_ids = set(collection.get(include=[])['ids']) # Get all existing IDs
        print(f"Found {len(existing_ids)} existing documents in collection '{collection_name}'. Will skip them.")
    except Exception as e:
        print(f"Warning: Could not retrieve existing IDs from collection '{collection_name}': {e}. Will proceed to add all documents.")
        existing_ids = set()

    for filename in tqdm(filenames, desc=f"Processing {case_type_display_name}"):
        if filename in existing_ids:
            # print(f"Skipping {filename} as it already exists in the collection.")
            continue

        filepath = os.path.join(cases_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                content = file.read()
            
            if not content.strip():
                print(f"Skipping empty file: {filename}")
                continue

            documents_batch.append(content)
            metadatas_batch.append({
                "filename": filename,
                "case_type": case_type_display_name, # Store the display name as metadata
                "source_folder": case_type_folder_name # Store the folder name as well
            })
            # ChromaDB IDs must be strings. Filename is a good candidate.
            ids_batch.append(filename) 

            if len(documents_batch) >= BATCH_SIZE:
                try:
                    collection.add(
                        documents=documents_batch,
                        metadatas=metadatas_batch,
                        ids=ids_batch
                    )
                    # print(f"Added batch of {len(ids_batch)} documents to {collection_name}.")
                except Exception as e:
                    print(f"Error adding batch to ChromaDB for {collection_name}: {e}")
                    # Potentially log failed IDs/documents for retry
                finally:
                    documents_batch, metadatas_batch, ids_batch = [], [], [] # Reset batches
        
        except Exception as e:
            print(f"Error processing file {filename}: {e}")
            # Continue with the next file

    # Add any remaining documents in the last batch
    if documents_batch:
        try:
            collection.add(
                documents=documents_batch,
                metadatas=metadatas_batch,
                ids=ids_batch
            )
            # print(f"Added final batch of {len(ids_batch)} documents to {collection_name}.")
        except Exception as e:
            print(f"Error adding final batch to ChromaDB for {collection_name}: {e}")

    print(f"Finished processing for {case_type_display_name}. Total documents in collection '{collection_name}': {collection.count()}")

if __name__ == "__main__":
    # --- 定义要处理的案件类型和对应的文件夹 ---
    # 格式: ("用户友好的显示名称", "实际的文件夹名称")
    # 文件夹名称用于定位 cases/ 子目录，并用于生成ChromaDB集合名
    case_types_to_process = [
        ("国家赔偿案例", "国家赔偿案例"),
        ("民事案例", "民事案例"),
        ("刑事案例", "刑事案例"),
        ("行政案例", "行政案例"),
        ("执行案例", "执行案例"),
        # ("指导案", "指导案"), # 已移除，因为目录不存在且不需要处理
    ]

    # 可以通过命令行参数选择要处理的类型，或默认处理所有
    # For now, let's focus on the first one as requested, or allow specific selection
    
    selected_case_type_folder = None
    if len(sys.argv) > 1:
        target_folder_arg = sys.argv[1]
        found = False
        for display_name, folder_name in case_types_to_process:
            if folder_name == target_folder_arg:
                process_and_store_cases(display_name, folder_name)
                found = True
                break
        if not found:
            print(f"Error: Specified case type folder '{target_folder_arg}' not defined in script for processing.")
            print("Available folder names for processing are:")
            for _, folder_name in case_types_to_process:
                print(f"  - {folder_name}")
    else:
        print("No specific case type folder provided as argument.")
        print("Processing all defined case types sequentially as no specific type was provided.")
        # 默认处理所有定义的案件类型
        for display_name, folder_name in case_types_to_process:
            process_and_store_cases(display_name, folder_name)
        
    print("\n--- All specified processing complete. ---") 