#!/usr/bin/env python3
"""
数据库状态检查脚本
"""

import os
import chromadb
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_database_status():
    """检查数据库状态"""
    db_path = "db/"
    
    logger.info("🔍 检查数据库状态...")
    
    # 检查数据库目录
    if not os.path.exists(db_path):
        logger.error("❌ 数据库目录不存在")
        return False
    
    # 检查目录内容
    db_files = os.listdir(db_path)
    logger.info(f"📁 数据库目录内容: {db_files}")
    
    try:
        # 尝试连接ChromaDB
        client = chromadb.PersistentClient(path=db_path)
        collections = client.list_collections()
        
        logger.info(f"📊 数据库状态:")
        logger.info(f"   - 集合数量: {len(collections)}")
        
        if len(collections) == 0:
            logger.warning("⚠️  数据库为空，没有任何集合")
            return False
        
        total_docs = 0
        for collection_info in collections:
            try:
                collection = client.get_collection(collection_info.name)
                count = collection.count()
                total_docs += count
                logger.info(f"   - {collection_info.name}: {count} 个文档")
            except Exception as e:
                logger.error(f"   - {collection_info.name}: 访问失败 ({e})")
        
        logger.info(f"   - 总文档数: {total_docs}")
        
        if total_docs > 0:
            logger.info("✅ 数据库状态正常")
            return True
        else:
            logger.warning("⚠️  数据库中没有文档")
            return False
        
    except Exception as e:
        logger.error(f"❌ 数据库连接失败: {e}")
        return False

def main():
    """主函数"""
    logger.info("🚀 开始检查数据库状态...")
    
    if check_database_status():
        logger.info("🎉 数据库检查完成，状态正常")
    else:
        logger.info("📋 数据库需要修复或重新导入")
        logger.info("💡 建议:")
        logger.info("   1. 如果数据库为空，运行: python restore_database.py")
        logger.info("   2. 如果有兼容性问题，运行: python fix_db_compatibility.py")

if __name__ == "__main__":
    main() 