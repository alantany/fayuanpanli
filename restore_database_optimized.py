#!/usr/bin/env python3
"""
法院判例知识库 - 优化的数据库恢复脚本
避免在云端下载embedding模型，使用预计算的向量
"""

import os
import sys
import shutil
import json
import chromadb
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clean_and_recreate_db():
    """完全清理并重新创建数据库目录"""
    db_path = "db/"
    
    logger.info("🧹 完全清理数据库目录...")
    
    # 完全删除数据库目录
    if os.path.exists(db_path):
        shutil.rmtree(db_path)
        logger.info("✅ 已删除旧数据库目录")
    
    # 重新创建目录
    os.makedirs(db_path, exist_ok=True)
    logger.info("✅ 已创建新数据库目录")
    
    # 设置正确的权限
    os.chmod(db_path, 0o755)
    logger.info("✅ 已设置目录权限")

def import_data_with_vectors():
    """从JSON格式导入数据，包含预计算的向量"""
    # 优先使用包含向量的JSON文件
    json_files = ["db_export_with_vectors.json", "db_export.json"]
    json_file = None
    
    logger.info("🔍 检查可用的JSON文件...")
    for file in json_files:
        if os.path.exists(file):
            file_size = os.path.getsize(file) / 1024 / 1024
            logger.info(f"   📁 找到文件: {file} ({file_size:.1f} MB)")
            if json_file is None:  # 使用第一个找到的文件（优先级顺序）
                json_file = file
                logger.info(f"   ✅ 选择使用: {file}")
    
    if not json_file:
        logger.error(f"❌ 未找到JSON导出文件")
        logger.info("请确保以下文件之一存在:")
        for file in json_files:
            logger.info(f"   - {file}")
        return False
    
    logger.info(f"📥 从JSON导入数据: {json_file}")
    
    try:
        logger.info("📖 读取JSON文件...")
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 显示导入信息
        metadata = data.get("_metadata", {})
        includes_vectors = metadata.get("includes_vectors", False)
        
        logger.info(f"📊 导入信息:")
        logger.info(f"   - 文件名: {json_file}")
        logger.info(f"   - 源平台: {metadata.get('source_platform', 'unknown')}")
        logger.info(f"   - 导出时间: {metadata.get('export_time', 'unknown')}")
        logger.info(f"   - 总文档数: {metadata.get('total_documents', 'unknown')}")
        logger.info(f"   - 包含向量: {'✅' if includes_vectors else '❌'}")
        
        if includes_vectors:
            logger.info("🎯 检测到预计算向量，将避免模型下载")
        else:
            logger.warning("⚠️  未检测到向量数据，可能会触发模型下载")
        
        # 初始化ChromaDB客户端
        logger.info("🔗 初始化ChromaDB客户端...")
        client = chromadb.PersistentClient(path="db/")
        total_imported = 0
        
        for collection_name, collection_data in data.items():
            # 跳过元数据
            if collection_name == "_metadata":
                continue
                
            logger.info(f"📥 导入集合: {collection_name}")
            
            try:
                # 创建集合
                collection = client.get_or_create_collection(name=collection_name)
                
                # 检查集合数据结构
                if not isinstance(collection_data, dict):
                    logger.error(f"❌ 集合数据格式错误: {collection_name}")
                    continue
                
                documents = collection_data.get('documents', [])
                metadatas = collection_data.get('metadatas', [])
                ids = collection_data.get('ids', [])
                embeddings = collection_data.get('embeddings', [])
                
                logger.info(f"   📊 集合数据统计:")
                logger.info(f"      - 文档数: {len(documents)}")
                logger.info(f"      - 元数据数: {len(metadatas)}")
                logger.info(f"      - ID数: {len(ids)}")
                logger.info(f"      - 向量数: {len(embeddings)}")
                
                if documents and len(documents) > 0:
                    # 确保所有数据数量匹配
                    if not metadatas:
                        metadatas = [{}] * len(documents)
                    if not ids:
                        ids = [f"doc_{i}" for i in range(len(documents))]
                    
                    # 如果有预计算的向量，使用它们；否则让ChromaDB计算
                    if embeddings and len(embeddings) == len(documents):
                        logger.info(f"   🎯 使用预计算向量，避免模型下载")
                        # 批量导入数据（包含向量）
                        batch_size = 100  # 增加批次大小，因为不需要计算向量
                        for i in range(0, len(documents), batch_size):
                            batch_docs = documents[i:i+batch_size]
                            batch_metas = metadatas[i:i+batch_size]
                            batch_ids = ids[i:i+batch_size]
                            batch_embeddings = embeddings[i:i+batch_size]
                            
                            # 确保批次数据长度一致
                            min_len = min(len(batch_docs), len(batch_metas), len(batch_ids), len(batch_embeddings))
                            batch_docs = batch_docs[:min_len]
                            batch_metas = batch_metas[:min_len]
                            batch_ids = batch_ids[:min_len]
                            batch_embeddings = batch_embeddings[:min_len]
                            
                            collection.add(
                                documents=batch_docs,
                                metadatas=batch_metas,
                                ids=batch_ids,
                                embeddings=batch_embeddings
                            )
                            
                            logger.info(f"   ✅ 导入批次 {i//batch_size + 1}: {len(batch_docs)} 个文档（含向量）")
                    else:
                        logger.warning(f"   ⚠️  没有预计算向量，将触发模型下载")
                        # 批量导入数据（不含向量，会触发embedding计算）
                        batch_size = 20  # 减小批次大小，避免内存问题
                        for i in range(0, len(documents), batch_size):
                            batch_docs = documents[i:i+batch_size]
                            batch_metas = metadatas[i:i+batch_size]
                            batch_ids = ids[i:i+batch_size]
                            
                            # 确保批次数据长度一致
                            min_len = min(len(batch_docs), len(batch_metas), len(batch_ids))
                            batch_docs = batch_docs[:min_len]
                            batch_metas = batch_metas[:min_len]
                            batch_ids = batch_ids[:min_len]
                            
                            collection.add(
                                documents=batch_docs,
                                metadatas=batch_metas,
                                ids=batch_ids
                            )
                            
                            logger.info(f"   ✅ 导入批次 {i//batch_size + 1}: {len(batch_docs)} 个文档")
                    
                    total_imported += len(documents)
                    logger.info(f"✅ 完成导入 {len(documents)} 个文档到 {collection_name}")
                else:
                    logger.warning(f"⚠️  集合 {collection_name} 没有文档数据")
                
            except Exception as e:
                logger.error(f"❌ 导入集合失败 {collection_name}: {e}")
                continue
        
        logger.info(f"✅ JSON数据导入完成，总计导入 {total_imported} 个文档")
        return True
        
    except Exception as e:
        logger.error(f"❌ JSON导入失败: {e}")
        return False

def verify_database():
    """验证数据库状态"""
    logger.info("🔍 验证数据库状态...")
    
    try:
        client = chromadb.PersistentClient(path="db/")
        collections = client.list_collections()
        
        if len(collections) == 0:
            logger.error("❌ 数据库为空")
            return False
        
        total_docs = 0
        for collection_info in collections:
            collection = client.get_collection(collection_info.name)
            count = collection.count()
            total_docs += count
            logger.info(f"   📁 {collection_info.name}: {count} 个文档")
        
        logger.info(f"✅ 验证成功: {len(collections)} 个集合，{total_docs} 个文档")
        return True
        
    except Exception as e:
        logger.error(f"❌ 验证失败: {e}")
        return False

def main():
    """主函数"""
    logger.info("🚀 开始优化数据库恢复...")
    
    # 检查JSON文件
    if not os.path.exists("db_export.json"):
        logger.error("❌ 未找到 db_export.json 文件")
        logger.info("请确保JSON导出文件存在")
        return
    
    # 完全清理并重新创建数据库
    clean_and_recreate_db()
    
    # 导入JSON数据
    if import_data_with_vectors():
        # 验证结果
        if verify_database():
            logger.info("🎉 优化数据库恢复完成！")
            logger.info("💡 提示：如果使用了预计算向量，已避免模型下载")
        else:
            logger.error("❌ 数据库验证失败")
    else:
        logger.error("❌ 数据导入失败")

if __name__ == "__main__":
    main() 