#!/usr/bin/env python3
"""
法院判例知识库 - 导出数据库（包含向量）
为云端部署准备包含预计算向量的JSON文件
"""

import os
import json
import chromadb
import logging
from datetime import datetime
import platform

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def export_database_with_vectors():
    """导出数据库，包含向量数据"""
    db_path = "db/"
    output_file = "db_export_with_vectors.json"
    
    if not os.path.exists(db_path):
        logger.error(f"❌ 数据库目录不存在: {db_path}")
        return False
    
    logger.info("📤 开始导出数据库（包含向量）...")
    
    try:
        # 连接到数据库
        client = chromadb.PersistentClient(path=db_path)
        collections = client.list_collections()
        
        if not collections:
            logger.error("❌ 数据库中没有集合")
            return False
        
        export_data = {}
        total_documents = 0
        
        # 导出每个集合
        for collection_info in collections:
            collection_name = collection_info.name
            logger.info(f"📥 导出集合: {collection_name}")
            
            try:
                collection = client.get_collection(collection_name)
                
                # 获取集合中的所有数据（包含向量）
                result = collection.get(
                    include=['documents', 'metadatas', 'embeddings']
                )
                
                documents = result.get('documents', [])
                metadatas = result.get('metadatas', [])
                ids = result.get('ids', [])
                embeddings = result.get('embeddings', [])
                
                logger.info(f"   📊 文档数: {len(documents)}")
                logger.info(f"   📊 向量数: {len(embeddings)}")
                
                # 验证数据完整性
                if len(documents) != len(embeddings):
                    logger.warning(f"   ⚠️  文档数和向量数不匹配: {len(documents)} vs {len(embeddings)}")
                
                export_data[collection_name] = {
                    'documents': documents,
                    'metadatas': metadatas,
                    'ids': ids,
                    'embeddings': embeddings
                }
                
                total_documents += len(documents)
                logger.info(f"   ✅ 集合 {collection_name} 导出完成")
                
            except Exception as e:
                logger.error(f"❌ 导出集合失败 {collection_name}: {e}")
                continue
        
        # 添加元数据
        export_data["_metadata"] = {
            "export_time": datetime.now().isoformat(),
            "source_platform": f"{platform.system()}_{platform.machine()}",
            "total_collections": len(collections),
            "total_documents": total_documents,
            "includes_vectors": True,
            "vector_dimension": len(embeddings[0]) if embeddings and len(embeddings) > 0 else None
        }
        
        # 保存到JSON文件
        logger.info(f"💾 保存到文件: {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        # 显示文件大小
        file_size = os.path.getsize(output_file) / 1024 / 1024
        logger.info(f"✅ 导出完成!")
        logger.info(f"📊 导出统计:")
        logger.info(f"   - 集合数量: {len(collections)}")
        logger.info(f"   - 总文档数: {total_documents}")
        logger.info(f"   - 文件大小: {file_size:.1f} MB")
        logger.info(f"   - 包含向量: ✅")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 导出失败: {e}")
        return False

def main():
    """主函数"""
    logger.info("🚀 开始导出数据库（包含向量）...")
    
    if export_database_with_vectors():
        logger.info("🎉 数据库导出成功！")
        logger.info("📋 下一步:")
        logger.info("1. 将 db_export_with_vectors.json 上传到云端")
        logger.info("2. 在云端运行: python restore_database_optimized.py")
        logger.info("3. 这样可以避免在云端下载embedding模型")
    else:
        logger.error("❌ 数据库导出失败")

if __name__ == "__main__":
    main() 