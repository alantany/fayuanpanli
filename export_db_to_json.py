#!/usr/bin/env python3
"""
法院判例知识库 - 数据库导出脚本
将ChromaDB数据导出为跨平台兼容的JSON格式
用于解决macOS M4和Ubuntu ARM之间的兼容性问题
"""

import os
import json
import chromadb
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def export_chromadb_to_json():
    """将ChromaDB数据导出为JSON格式"""
    db_path = "db/"
    output_file = "db_export.json"
    
    logger.info("🚀 开始导出ChromaDB数据...")
    
    if not os.path.exists(db_path):
        logger.error(f"❌ 数据库目录不存在: {db_path}")
        return False
    
    try:
        # 连接ChromaDB
        client = chromadb.PersistentClient(path=db_path)
        collections = client.list_collections()
        
        logger.info(f"📊 找到 {len(collections)} 个集合")
        
        export_data = {}
        total_documents = 0
        
        for collection_info in collections:
            collection_name = collection_info.name
            logger.info(f"📤 导出集合: {collection_name}")
            
            try:
                # 获取集合
                collection = client.get_collection(name=collection_name)
                
                # 获取所有数据
                result = collection.get(
                    include=["documents", "metadatas", "embeddings"]
                )
                
                # 准备导出数据
                collection_data = {
                    "documents": result.get("documents", []),
                    "metadatas": result.get("metadatas", []),
                    "ids": result.get("ids", []),
                    # 注意：不导出embeddings，因为云端会重新生成
                    "count": len(result.get("documents", []))
                }
                
                export_data[collection_name] = collection_data
                total_documents += collection_data["count"]
                
                logger.info(f"✅ 集合 {collection_name}: {collection_data['count']} 个文档")
                
            except Exception as e:
                logger.error(f"❌ 导出集合失败 {collection_name}: {e}")
                continue
        
        # 添加元数据
        export_data["_metadata"] = {
            "export_time": datetime.now().isoformat(),
            "source_platform": "macOS_M4",
            "total_collections": len(collections),
            "total_documents": total_documents,
            "chromadb_version": chromadb.__version__
        }
        
        # 保存到JSON文件
        logger.info(f"💾 保存到文件: {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        # 显示文件大小
        file_size = os.path.getsize(output_file) / 1024 / 1024
        logger.info(f"✅ 导出完成！")
        logger.info(f"📊 导出摘要:")
        logger.info(f"   - 集合数量: {len(collections)}")
        logger.info(f"   - 文档总数: {total_documents}")
        logger.info(f"   - 文件大小: {file_size:.2f} MB")
        logger.info(f"   - 输出文件: {output_file}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 导出失败: {e}")
        return False

def verify_export_file():
    """验证导出文件的完整性"""
    output_file = "db_export.json"
    
    if not os.path.exists(output_file):
        logger.error(f"❌ 导出文件不存在: {output_file}")
        return False
    
    try:
        logger.info("🔍 验证导出文件...")
        
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        metadata = data.get("_metadata", {})
        logger.info(f"✅ 验证成功")
        logger.info(f"   - 导出时间: {metadata.get('export_time')}")
        logger.info(f"   - 源平台: {metadata.get('source_platform')}")
        logger.info(f"   - 集合数量: {metadata.get('total_collections')}")
        logger.info(f"   - 文档总数: {metadata.get('total_documents')}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 验证失败: {e}")
        return False

def main():
    """主函数"""
    logger.info("🎯 ChromaDB跨平台数据导出工具")
    logger.info("📋 用途: 解决macOS M4和Ubuntu ARM之间的数据库兼容性问题")
    
    # 导出数据
    if export_chromadb_to_json():
        # 验证导出文件
        if verify_export_file():
            logger.info("🎉 导出和验证完成！")
            logger.info("")
            logger.info("📋 下一步操作:")
            logger.info("1. 将 db_export.json 文件上传到云端服务器")
            logger.info("2. 在云端运行: python fix_db_compatibility.py")
            logger.info("3. 验证云端数据库是否正常工作")
        else:
            logger.error("❌ 导出文件验证失败")
    else:
        logger.error("❌ 数据导出失败")

if __name__ == "__main__":
    main() 