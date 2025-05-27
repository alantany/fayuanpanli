#!/usr/bin/env python3
"""
调试脚本：检查ChromaDB中的集合
"""

import chromadb
import sys

def main():
    try:
        # 连接到数据库
        client = chromadb.PersistentClient(path="./db")
        print("✅ 成功连接到数据库")
        
        # 列出所有集合
        collections = client.list_collections()
        print(f"\n📊 数据库中共有 {len(collections)} 个集合:")
        
        for i, collection in enumerate(collections, 1):
            print(f"{i}. {collection.name}")
            
            # 获取集合详细信息
            try:
                count = collection.count()
                print(f"   - 文档数量: {count}")
                
                # 获取一些示例数据
                if count > 0:
                    sample = collection.peek(limit=1)
                    if sample['metadatas'] and sample['metadatas'][0]:
                        metadata = sample['metadatas'][0]
                        if 'filename' in metadata:
                            print(f"   - 示例文件: {metadata['filename']}")
                            
            except Exception as e:
                print(f"   - 错误: {e}")
        
        print("\n🔍 测试集合名称生成:")
        from app_cloud import get_clean_collection_name
        
        test_cases = ["民事案例", "刑事案例", "行政案例", "执行案例", "国家赔偿案例"]
        for case_type in test_cases:
            collection_name = get_clean_collection_name(case_type)
            print(f"'{case_type}' -> '{collection_name}'")
            
            # 检查是否存在
            try:
                collection = client.get_collection(name=collection_name)
                count = collection.count()
                print(f"   ✅ 存在，包含 {count} 个文档")
            except Exception as e:
                print(f"   ❌ 不存在: {e}")
                
    except Exception as e:
        print(f"❌ 连接数据库失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 