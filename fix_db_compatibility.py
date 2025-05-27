#!/usr/bin/env python3
"""
法院判例知识库 - 数据库兼容性修复脚本
解决macOS M4和Ubuntu ARM之间的ChromaDB兼容性问题
"""

import os
import sys
import shutil
import sqlite3
import chromadb
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_database_compatibility():
    """检查数据库兼容性"""
    db_path = "db/"
    
    logger.info("🔍 检查数据库兼容性...")
    
    # 检查数据库目录是否存在
    if not os.path.exists(db_path):
        logger.error(f"❌ 数据库目录不存在: {db_path}")
        return False
    
    # 检查SQLite文件
    sqlite_files = list(Path(db_path).rglob("*.sqlite3"))
    if not sqlite_files:
        logger.error("❌ 未找到SQLite数据库文件")
        return False
    
    # 尝试连接ChromaDB
    try:
        client = chromadb.PersistentClient(path=db_path)
        collections = client.list_collections()
        
        # 检查集合数量
        if len(collections) == 0:
            logger.warning("⚠️  数据库为空，没有任何集合")
            return False
        
        # 检查文档数量
        total_docs = 0
        for collection_info in collections:
            try:
                collection = client.get_collection(collection_info.name)
                count = collection.count()
                total_docs += count
            except Exception as e:
                logger.warning(f"⚠️  集合 {collection_info.name} 访问异常: {e}")
        
        if total_docs == 0:
            logger.warning("⚠️  数据库中没有任何文档")
            return False
        
        logger.info(f"✅ 数据库连接成功，找到 {len(collections)} 个集合，{total_docs} 个文档")
        return True
        
    except Exception as e:
        logger.error(f"❌ 数据库连接失败: {str(e)}")
        if "no such column: collections.topic" in str(e):
            logger.error("🔧 检测到跨平台兼容性问题")
        return False

def backup_database():
    """备份现有数据库"""
    db_path = "db/"
    backup_path = f"db_backup_{int(__import__('time').time())}"
    
    if os.path.exists(db_path):
        logger.info(f"📦 备份数据库到: {backup_path}")
        shutil.copytree(db_path, backup_path)
        return backup_path
    return None

def create_empty_compatible_database():
    """创建空的兼容数据库结构"""
    db_path = "db/"
    
    logger.info("🔧 创建兼容的空数据库结构...")
    
    # 删除现有数据库
    if os.path.exists(db_path):
        shutil.rmtree(db_path)
    
    # 创建新的数据库目录
    os.makedirs(db_path, exist_ok=True)
    
    try:
        # 初始化ChromaDB客户端
        client = chromadb.PersistentClient(path=db_path)
        
        # 创建所有需要的集合（空集合）
        collection_names = [
            "knowledge_base_min_shi_an_li",
            "knowledge_base_xing_shi_an_li", 
            "knowledge_base_xing_zheng_an_li",
            "knowledge_base_zhi_xing_an_li",
            "knowledge_base_guo_jia_pei_chang_an_li"
        ]
        
        for name in collection_names:
            try:
                collection = client.get_or_create_collection(name=name)
                logger.info(f"✅ 创建集合: {name}")
            except Exception as e:
                logger.error(f"❌ 创建集合失败 {name}: {e}")
        
        logger.info("✅ 兼容数据库结构创建完成")
        return True
        
    except Exception as e:
        logger.error(f"❌ 创建兼容数据库失败: {e}")
        return False

def export_data_to_json():
    """将数据导出为JSON格式（跨平台兼容）"""
    logger.info("📤 导出数据为JSON格式...")
    
    # 这个功能需要在本地macOS环境执行
    # 云端只需要导入JSON数据
    logger.info("ℹ️  此功能需要在本地macOS环境执行")
    logger.info("ℹ️  请在本地运行: python export_db_to_json.py")
    
def import_data_from_json():
    """从JSON格式导入数据"""
    json_file = "db_export.json"
    
    if not os.path.exists(json_file):
        logger.error(f"❌ JSON导出文件不存在: {json_file}")
        logger.info("ℹ️  请先在本地运行导出脚本")
        return False
    
    logger.info("📥 从JSON导入数据...")
    
    try:
        import json
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 显示导入信息
        metadata = data.get("_metadata", {})
        logger.info(f"📊 导入信息:")
        logger.info(f"   - 源平台: {metadata.get('source_platform', 'unknown')}")
        logger.info(f"   - 导出时间: {metadata.get('export_time', 'unknown')}")
        logger.info(f"   - 总文档数: {metadata.get('total_documents', 'unknown')}")
        
        client = chromadb.PersistentClient(path="db/")
        total_imported = 0
        
        for collection_name, collection_data in data.items():
            # 跳过元数据
            if collection_name == "_metadata":
                continue
                
            logger.info(f"📥 导入集合: {collection_name}")
            
            try:
                collection = client.get_or_create_collection(name=collection_name)
                
                # 检查集合数据结构
                if not isinstance(collection_data, dict):
                    logger.error(f"❌ 集合数据格式错误: {collection_name}")
                    continue
                
                documents = collection_data.get('documents', [])
                metadatas = collection_data.get('metadatas', [])
                ids = collection_data.get('ids', [])
                
                if documents and len(documents) > 0:
                    # 批量导入数据
                    batch_size = 100  # 分批导入，避免内存问题
                    for i in range(0, len(documents), batch_size):
                        batch_docs = documents[i:i+batch_size]
                        batch_metas = metadatas[i:i+batch_size] if metadatas else [{}] * len(batch_docs)
                        batch_ids = ids[i:i+batch_size] if ids else [f"doc_{j}" for j in range(i, i+len(batch_docs))]
                        
                        collection.add(
                            documents=batch_docs,
                            metadatas=batch_metas,
                            ids=batch_ids
                        )
                    
                    total_imported += len(documents)
                    logger.info(f"✅ 导入 {len(documents)} 个文档到 {collection_name}")
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

def main():
    """主函数"""
    logger.info("🚀 开始数据库兼容性修复...")
    
    # 检查当前数据库状态
    if check_database_compatibility():
        logger.info("✅ 数据库兼容性正常，无需修复")
        return
    
    # 备份现有数据库
    backup_path = backup_database()
    if backup_path:
        logger.info(f"✅ 数据库已备份到: {backup_path}")
    
    # 检查是否有JSON导出文件
    if os.path.exists("db_export.json"):
        logger.info("📁 发现JSON导出文件，尝试导入...")
        
        # 创建兼容的空数据库
        if create_empty_compatible_database():
            # 导入JSON数据
            if import_data_from_json():
                logger.info("🎉 数据库兼容性修复完成！")
                
                # 验证修复结果
                if check_database_compatibility():
                    logger.info("✅ 修复验证成功")
                else:
                    logger.error("❌ 修复验证失败")
            else:
                logger.error("❌ JSON数据导入失败")
        else:
            logger.error("❌ 创建兼容数据库失败")
    else:
        logger.info("📋 修复步骤:")
        logger.info("1. 在本地macOS环境运行: python export_db_to_json.py")
        logger.info("2. 将生成的 db_export.json 文件上传到云端")
        logger.info("3. 在云端重新运行此脚本")
        
        # 创建空的兼容数据库结构
        create_empty_compatible_database()

if __name__ == "__main__":
    main() 