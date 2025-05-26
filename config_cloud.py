"""
法院判例知识库 - 云端部署配置
针对1C2G服务器优化的配置参数
"""

import os
from dotenv import load_dotenv

load_dotenv()

# === Embedding API 配置 ===
EMBEDDING_API_PROVIDER = os.getenv("EMBEDDING_API_PROVIDER", "openai")
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "text-embedding-3-small")
EMBEDDING_API_URL = os.getenv("EMBEDDING_API_URL", "https://api.openai.com/v1/embeddings")

# === 资源限制配置 ===
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "10"))  # 降低批处理大小
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "1"))  # 限制并发数
MEMORY_LIMIT_MB = int(os.getenv("MEMORY_LIMIT", "1500"))  # 内存限制

# === ChromaDB 配置 ===
CHROMA_DATA_PATH = os.getenv("CHROMA_DATA_PATH", "db/")
COLLECTION_NAME_PREFIX = "knowledge_base_"

# === Flask 配置 ===
FLASK_HOST = os.getenv("FLASK_HOST", "127.0.0.1")
FLASK_PORT = int(os.getenv("FLASK_PORT", "5001"))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"

# === LLM 配置 (保持原有) ===
LLM_API_URL = os.getenv("LLM_API_URL")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME")

# === 缓存配置 ===
ENABLE_EMBEDDING_CACHE = os.getenv("ENABLE_EMBEDDING_CACHE", "True").lower() == "true"
CACHE_DIR = os.getenv("CACHE_DIR", "cache/")
CACHE_MAX_SIZE_MB = int(os.getenv("CACHE_MAX_SIZE_MB", "100"))

# === API 限制配置 ===
API_RATE_LIMIT = int(os.getenv("API_RATE_LIMIT", "60"))  # 每分钟请求数
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))  # 超时时间(秒)
API_RETRY_TIMES = int(os.getenv("API_RETRY_TIMES", "3"))  # 重试次数

# === 监控配置 ===
ENABLE_MONITORING = os.getenv("ENABLE_MONITORING", "True").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# === 验证配置 ===
def validate_config():
    """验证必要的配置项"""
    errors = []
    
    if not EMBEDDING_API_KEY:
        errors.append("EMBEDDING_API_KEY is required")
    
    if EMBEDDING_API_PROVIDER not in ["openai", "azure", "cohere"]:
        errors.append(f"Unsupported EMBEDDING_API_PROVIDER: {EMBEDDING_API_PROVIDER}")
    
    if errors:
        raise ValueError("Configuration errors: " + "; ".join(errors))
    
    return True

# === 支持的Embedding模型配置 ===
EMBEDDING_MODELS = {
    "openai": {
        "text-embedding-3-small": {"dimensions": 1536, "max_tokens": 8191},
        "text-embedding-3-large": {"dimensions": 3072, "max_tokens": 8191},
        "text-embedding-ada-002": {"dimensions": 1536, "max_tokens": 8191}
    },
    "azure": {
        "text-embedding-ada-002": {"dimensions": 1536, "max_tokens": 8191}
    },
    "cohere": {
        "embed-multilingual-v3.0": {"dimensions": 1024, "max_tokens": 512}
    }
}

def get_embedding_dimensions():
    """获取当前embedding模型的维度"""
    provider_models = EMBEDDING_MODELS.get(EMBEDDING_API_PROVIDER, {})
    model_config = provider_models.get(EMBEDDING_MODEL_NAME, {})
    return model_config.get("dimensions", 1536)  # 默认1536维

def get_max_tokens():
    """获取当前embedding模型的最大token数"""
    provider_models = EMBEDDING_MODELS.get(EMBEDDING_API_PROVIDER, {})
    model_config = provider_models.get(EMBEDDING_MODEL_NAME, {})
    return model_config.get("max_tokens", 8191)  # 默认8191 