#!/usr/bin/env python3
"""
法院判例知识库 - 数据库恢复脚本
从备份中恢复数据库
"""

import os
import shutil
import logging
import glob
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def list_available_backups():
    """列出可用的备份"""
    backup_pattern = "db_backup_*"
    backups = glob.glob(backup_pattern)
    
    if not backups:
        logger.error("❌ 未找到任何数据库备份")
        return []
    
    # 按时间戳排序（最新的在前）
    backups.sort(reverse=True)
    
    logger.info(f"📁 找到 {len(backups)} 个备份:")
    for i, backup in enumerate(backups):
        backup_time = backup.split('_')[-1]
        size = get_directory_size(backup)
        logger.info(f"   {i+1}. {backup} (时间戳: {backup_time}, 大小: {size:.1f}MB)")
    
    return backups

def get_directory_size(path):
    """获取目录大小（MB）"""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if os.path.exists(filepath):
                total_size += os.path.getsize(filepath)
    return total_size / 1024 / 1024

def restore_from_backup(backup_path):
    """从指定备份恢复数据库"""
    db_path = "db/"
    
    if not os.path.exists(backup_path):
        logger.error(f"❌ 备份目录不存在: {backup_path}")
        return False
    
    logger.info(f"🔄 从备份恢复数据库: {backup_path}")
    
    try:
        # 删除当前数据库目录
        if os.path.exists(db_path):
            logger.info("🗑️  删除当前数据库目录...")
            shutil.rmtree(db_path)
        
        # 从备份复制数据库
        logger.info("📋 复制备份数据...")
        shutil.copytree(backup_path, db_path)
        
        logger.info("✅ 数据库恢复完成")
        return True
        
    except Exception as e:
        logger.error(f"❌ 恢复失败: {e}")
        return False

def verify_restored_database():
    """验证恢复的数据库"""
    db_path = "db/"
    
    if not os.path.exists(db_path):
        logger.error("❌ 数据库目录不存在")
        return False
    
    try:
        import chromadb
        
        client = chromadb.PersistentClient(path=db_path)
        collections = client.list_collections()
        
        logger.info(f"✅ 数据库验证成功")
        logger.info(f"📊 数据库状态:")
        logger.info(f"   - 集合数量: {len(collections)}")
        
        total_docs = 0
        for collection_info in collections:
            try:
                collection = client.get_collection(collection_info.name)
                count = collection.count()
                total_docs += count
                logger.info(f"   - {collection_info.name}: {count} 个文档")
            except Exception as e:
                logger.warning(f"   - {collection_info.name}: 无法获取文档数量 ({e})")
        
        logger.info(f"   - 总文档数: {total_docs}")
        return True
        
    except Exception as e:
        logger.error(f"❌ 数据库验证失败: {e}")
        return False

def main():
    """主函数"""
    logger.info("🔧 数据库恢复工具")
    
    # 列出可用备份
    backups = list_available_backups()
    if not backups:
        return
    
    # 自动选择最新的备份
    latest_backup = backups[0]
    logger.info(f"🎯 自动选择最新备份: {latest_backup}")
    
    # 确认恢复
    logger.info("⚠️  警告: 此操作将删除当前数据库并从备份恢复")
    
    # 执行恢复
    if restore_from_backup(latest_backup):
        # 验证恢复结果
        if verify_restored_database():
            logger.info("🎉 数据库恢复成功！")
            logger.info("")
            logger.info("📋 下一步:")
            logger.info("1. 测试数据库功能: python -c \"import chromadb; print('数据库正常')\"")
            logger.info("2. 启动应用: python app_cloud.py")
        else:
            logger.error("❌ 数据库恢复后验证失败")
    else:
        logger.error("❌ 数据库恢复失败")

if __name__ == "__main__":
    main() 