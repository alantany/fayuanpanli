"""
法院判例知识库 - 云端向量化脚本
使用远程embedding API进行向量化，适合低资源环境
"""

import chromadb
import os
import sys
import re
import time
import logging
from tqdm import tqdm
from pypinyin import pinyin, Style
from pathlib import Path

# 导入云端配置和服务
from config_cloud import (
    CHROMA_DATA_PATH, COLLECTION_NAME_PREFIX, BATCH_SIZE,
    validate_config, get_embedding_dimensions
)
from embedding_service import get_embedding_service

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CloudEmbeddingFunction:
    """ChromaDB兼容的云端embedding函数"""
    
    def __init__(self):
        self.embedding_service = get_embedding_service()
        self.dimensions = get_embedding_dimensions()
    
    def __call__(self, input_texts):
        """ChromaDB调用接口"""
        if isinstance(input_texts, str):
            input_texts = [input_texts]
        
        return self.embedding_service.get_embeddings(input_texts)

def get_clean_collection_name(case_type_folder_name_raw):
    """根据案件类型的文件夹名生成一个清理过的、适合做集合名的字符串。"""
    # 将中文文件夹名转换为拼音
    pinyin_list = pinyin(case_type_folder_name_raw, style=Style.NORMAL)
    cleaned_name = "_".join([item[0] for item in pinyin_list if item[0]])
    
    cleaned_name = cleaned_name.lower()
    # 移除非法字符，仅保留字母、数字、下划线
    cleaned_name = re.sub(r'[^a-z0-9_]', '', cleaned_name)
    
    cleaned_name = cleaned_name.replace('-', '_')
    cleaned_name = re.sub(r'_+', '_', cleaned_name)
    cleaned_name = cleaned_name.strip('_')

    if not cleaned_name:
        timestamp_fallback = str(int(time.time()))[-6:]
        cleaned_name = f"default_topic_{timestamp_fallback}"

    # 确保符合长度限制
    prefix_len = len(COLLECTION_NAME_PREFIX)
    max_name_len = 63 - prefix_len
    
    if len(cleaned_name) > max_name_len:
        cleaned_name = cleaned_name[:max_name_len]
    
    cleaned_name = cleaned_name.strip('_')
    
    if not cleaned_name or len(cleaned_name) < 1:
        timestamp_fallback = str(int(time.time()))[-6:]
        cleaned_name = f"fallback_{timestamp_fallback}"

    full_collection_name = f"{COLLECTION_NAME_PREFIX}{cleaned_name}"
    
    # 最终检查ChromaDB的完整命名规则
    if not re.match(r"^[a-z0-9][a-z0-9_.-]{1,61}[a-z0-9]$", full_collection_name):
        safe_name_parts = []
        for char in cleaned_name:
            if 'a' <= char <= 'z' or '0' <= char <= '9' or char == '_':
                safe_name_parts.append(char)
        
        safe_cleaned_name = "".join(safe_name_parts).strip('_')
        
        if len(safe_cleaned_name) < 1:
            timestamp_fallback = str(int(time.time()))[-6:]
            safe_cleaned_name = f"gen_{timestamp_fallback}"

        safe_cleaned_name = safe_cleaned_name[:max_name_len]
        safe_cleaned_name = safe_cleaned_name.strip('_')
        
        if not safe_cleaned_name or not safe_cleaned_name[0].isalnum():
            safe_cleaned_name = "c" + safe_cleaned_name
        if not safe_cleaned_name[-1].isalnum():
            safe_cleaned_name = safe_cleaned_name + "e"
            
        safe_cleaned_name = safe_cleaned_name[:max_name_len]
        
        full_collection_name = f"{COLLECTION_NAME_PREFIX}{safe_cleaned_name}"
        
        if not re.match(r"^[a-z0-9][a-z0-9_.-]{1,61}[a-z0-9]$", full_collection_name):
            logger.warning(f"Could not generate compliant collection name for '{case_type_folder_name_raw}'. Using emergency fallback.")
            full_collection_name = f"{COLLECTION_NAME_PREFIX}emergency_{str(int(time.time()))[-8:]}"
            full_collection_name = full_collection_name[:63].strip('_.-')

    logger.info(f"Generated collection name: {full_collection_name}")
    return full_collection_name

def process_and_store_cases(case_type_display_name, case_type_folder_name):
    """
    处理指定案件类型目录下的所有 .txt 文件，将其向量化并存入ChromaDB。
    使用远程embedding API，适合云端部署。
    """
    collection_name = get_clean_collection_name(case_type_folder_name)
    cases_dir = os.path.join(case_type_folder_name, "cases")
    
    logger.info(f"\n--- Processing Case Type: {case_type_display_name} ---")
    logger.info(f"Target collection: {collection_name}")
    logger.info(f"Source directory: {os.path.abspath(cases_dir)}")

    if not os.path.isdir(cases_dir):
        logger.error(f"Cases directory not found: {cases_dir}")
        return

    filenames = [f for f in os.listdir(cases_dir) if f.endswith(".txt")]
    if not filenames:
        logger.warning(f"No .txt files found in {cases_dir}")
        return

    try:
        # 初始化ChromaDB客户端
        logger.info(f"Initializing ChromaDB client...")
        client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
        
        # 创建云端embedding函数
        logger.info(f"Initializing cloud embedding function...")
        ef = CloudEmbeddingFunction()
        
        # 获取或创建集合
        logger.info(f"Getting or creating collection: {collection_name}...")
        collection = client.get_or_create_collection(
            name=collection_name,
            embedding_function=ef
        )
        logger.info(f"Collection ready: {collection_name}")

    except Exception as e:
        logger.error(f"Error initializing ChromaDB or embedding service: {e}")
        logger.error("Please check your embedding API configuration and network connection.")
        return

    # 检查已存在的文档
    try:
        existing_ids = set(collection.get(include=[])['ids'])
        logger.info(f"Found {len(existing_ids)} existing documents in collection '{collection_name}'")
    except Exception as e:
        logger.warning(f"Could not retrieve existing IDs: {e}")
        existing_ids = set()

    documents_batch = []
    metadatas_batch = []
    ids_batch = []
    processed_count = 0
    skipped_count = 0
    
    for filename in tqdm(filenames, desc=f"Processing {case_type_display_name}"):
        # 跳过已存在的文档
        if filename in existing_ids:
            skipped_count += 1
            continue

        filepath = os.path.join(cases_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                content = file.read()
            
            if not content.strip():
                logger.warning(f"Skipping empty file: {filename}")
                continue

            documents_batch.append(content)
            metadatas_batch.append({
                "filename": filename,
                "case_type": case_type_display_name,
                "source_folder": case_type_folder_name
            })
            ids_batch.append(filename)

            # 当批次达到指定大小时，处理这一批
            if len(documents_batch) >= BATCH_SIZE:
                try:
                    logger.info(f"Processing batch of {len(documents_batch)} documents...")
                    collection.add(
                        documents=documents_batch,
                        metadatas=metadatas_batch,
                        ids=ids_batch
                    )
                    processed_count += len(documents_batch)
                    logger.info(f"Successfully added batch. Total processed: {processed_count}")
                    
                except Exception as e:
                    logger.error(f"Error adding batch to ChromaDB: {e}")
                    # 尝试逐个添加以找出问题文档
                    for i, (doc, meta, doc_id) in enumerate(zip(documents_batch, metadatas_batch, ids_batch)):
                        try:
                            collection.add(
                                documents=[doc],
                                metadatas=[meta],
                                ids=[doc_id]
                            )
                            processed_count += 1
                        except Exception as single_error:
                            logger.error(f"Failed to add document {doc_id}: {single_error}")
                
                finally:
                    # 重置批次
                    documents_batch, metadatas_batch, ids_batch = [], [], []
                    
                    # 添加短暂延迟以避免API限制
                    time.sleep(0.5)
        
        except Exception as e:
            logger.error(f"Error processing file {filename}: {e}")
            continue

    # 处理最后一批
    if documents_batch:
        try:
            logger.info(f"Processing final batch of {len(documents_batch)} documents...")
            collection.add(
                documents=documents_batch,
                metadatas=metadatas_batch,
                ids=ids_batch
            )
            processed_count += len(documents_batch)
            logger.info(f"Successfully added final batch.")
            
        except Exception as e:
            logger.error(f"Error adding final batch: {e}")
            # 尝试逐个添加
            for i, (doc, meta, doc_id) in enumerate(zip(documents_batch, metadatas_batch, ids_batch)):
                try:
                    collection.add(
                        documents=[doc],
                        metadatas=[meta],
                        ids=[doc_id]
                    )
                    processed_count += 1
                except Exception as single_error:
                    logger.error(f"Failed to add document {doc_id}: {single_error}")

    # 最终统计
    final_count = collection.count()
    logger.info(f"Processing complete for {case_type_display_name}:")
    logger.info(f"  - Files processed: {processed_count}")
    logger.info(f"  - Files skipped (already exist): {skipped_count}")
    logger.info(f"  - Total documents in collection: {final_count}")

def main():
    """主函数"""
    try:
        # 验证配置
        validate_config()
        logger.info("Configuration validated successfully")
        
        # 确保数据目录存在
        os.makedirs(CHROMA_DATA_PATH, exist_ok=True)
        
        # 定义要处理的案件类型
        case_types_to_process = [
            ("国家赔偿案例", "国家赔偿案例"),
            ("民事案例", "民事案例"),
            ("刑事案例", "刑事案例"),
            ("行政案例", "行政案例"),
            ("执行案例", "执行案例"),
        ]

        # 处理命令行参数
        if len(sys.argv) > 1:
            target_folder_arg = sys.argv[1]
            found = False
            for display_name, folder_name in case_types_to_process:
                if folder_name == target_folder_arg:
                    process_and_store_cases(display_name, folder_name)
                    found = True
                    break
            if not found:
                logger.error(f"Specified case type folder '{target_folder_arg}' not found")
                logger.info("Available folder names:")
                for _, folder_name in case_types_to_process:
                    logger.info(f"  - {folder_name}")
                return 1
        else:
            logger.info("Processing all case types...")
            for display_name, folder_name in case_types_to_process:
                try:
                    process_and_store_cases(display_name, folder_name)
                except Exception as e:
                    logger.error(f"Failed to process {display_name}: {e}")
                    continue
        
        logger.info("All processing complete!")
        return 0
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 