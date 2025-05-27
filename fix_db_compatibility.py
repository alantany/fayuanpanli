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
        logger.info(f"✅ 数据库连接成功，找到 {len(collections)} 个集合")
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
        
        client = chromadb.PersistentClient(path="db/")
        
        for collection_name, collection_data in data.items():
            logger.info(f"📥 导入集合: {collection_name}")
            
            try:
                collection = client.get_or_create_collection(name=collection_name)
                
                if collection_data['documents']:
                    collection.add(
                        documents=collection_data['documents'],
                        metadatas=collection_data['metadatas'],
                        ids=collection_data['ids']
                    )
                    logger.info(f"✅ 导入 {len(collection_data['documents'])} 个文档到 {collection_name}")
                
            except Exception as e:
                logger.error(f"❌ 导入集合失败 {collection_name}: {e}")
        
        logger.info("✅ JSON数据导入完成")
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