import chromadb
from chromadb.utils import embedding_functions

# 初始化ChromaDB客户端
client = chromadb.PersistentClient(path="db/")

# 列出所有集合
try:
    collections = client.list_collections()
    print(f"找到 {len(collections)} 个集合:")
    for collection in collections:
        print(f"  - {collection.name}")
        try:
            col = client.get_collection(collection.name)
            print(f"    集合 {collection.name} 包含 {col.count()} 个文档")
        except Exception as e:
            print(f"    错误: 无法访问集合 {collection.name}: {e}")
except Exception as e:
    print(f"错误: 无法列出集合: {e}") 