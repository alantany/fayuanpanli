"""
法院判例知识库 - 远程Embedding服务
支持多种API提供商的统一接口
"""

import os
import json
import hashlib
import time
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import requests
import tiktoken
from config_cloud import (
    EMBEDDING_API_PROVIDER, EMBEDDING_API_KEY, EMBEDDING_MODEL_NAME, 
    EMBEDDING_API_URL, API_TIMEOUT, API_RETRY_TIMES, ENABLE_EMBEDDING_CACHE,
    CACHE_DIR, get_embedding_dimensions, get_max_tokens
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmbeddingService:
    """统一的Embedding服务接口"""
    
    def __init__(self):
        self.provider = EMBEDDING_API_PROVIDER
        self.api_key = EMBEDDING_API_KEY
        self.model_name = EMBEDDING_MODEL_NAME
        self.api_url = EMBEDDING_API_URL
        self.dimensions = get_embedding_dimensions()
        self.max_tokens = get_max_tokens()
        
        # 初始化缓存
        if ENABLE_EMBEDDING_CACHE:
            self.cache_dir = Path(CACHE_DIR)
            self.cache_dir.mkdir(exist_ok=True)
        
        # 初始化tokenizer (用于OpenAI)
        if self.provider == "openai":
            try:
                self.tokenizer = tiktoken.get_encoding("cl100k_base")
            except Exception as e:
                logger.warning(f"Failed to load tokenizer: {e}")
                self.tokenizer = None
        
        logger.info(f"Embedding service initialized: {self.provider}/{self.model_name}")
    
    def _get_cache_key(self, text: str) -> str:
        """生成缓存键"""
        content = f"{self.provider}:{self.model_name}:{text}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[List[float]]:
        """从缓存获取embedding"""
        if not ENABLE_EMBEDDING_CACHE:
            return None
        
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    return data.get('embedding')
            except Exception as e:
                logger.warning(f"Failed to read cache {cache_key}: {e}")
        return None
    
    def _save_to_cache(self, cache_key: str, embedding: List[float]):
        """保存embedding到缓存"""
        if not ENABLE_EMBEDDING_CACHE:
            return
        
        cache_file = self.cache_dir / f"{cache_key}.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump({
                    'embedding': embedding,
                    'timestamp': time.time(),
                    'model': self.model_name
                }, f)
        except Exception as e:
            logger.warning(f"Failed to save cache {cache_key}: {e}")
    
    def _truncate_text(self, text: str) -> str:
        """截断文本以适应token限制"""
        if self.tokenizer and self.provider == "openai":
            tokens = self.tokenizer.encode(text)
            if len(tokens) > self.max_tokens:
                # 保留前90%的tokens，留出一些余量
                max_tokens = int(self.max_tokens * 0.9)
                truncated_tokens = tokens[:max_tokens]
                text = self.tokenizer.decode(truncated_tokens)
                logger.warning(f"Text truncated from {len(tokens)} to {len(truncated_tokens)} tokens")
        
        return text
    
    def _call_openai_api(self, texts: List[str]) -> List[List[float]]:
        """调用OpenAI Embedding API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "input": texts,
            "model": self.model_name,
            "encoding_format": "float"
        }
        
        response = requests.post(
            self.api_url,
            headers=headers,
            json=data,
            timeout=API_TIMEOUT
        )
        response.raise_for_status()
        
        result = response.json()
        embeddings = []
        
        for item in result["data"]:
            embeddings.append(item["embedding"])
        
        return embeddings
    
    def _call_cohere_api(self, texts: List[str]) -> List[List[float]]:
        """调用Cohere Embedding API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "texts": texts,
            "model": self.model_name,
            "input_type": "search_document"
        }
        
        response = requests.post(
            self.api_url,
            headers=headers,
            json=data,
            timeout=API_TIMEOUT
        )
        response.raise_for_status()
        
        result = response.json()
        return result["embeddings"]
    
    def _call_api_with_retry(self, texts: List[str]) -> List[List[float]]:
        """带重试的API调用"""
        last_error = None
        
        for attempt in range(API_RETRY_TIMES):
            try:
                if self.provider == "openai":
                    return self._call_openai_api(texts)
                elif self.provider == "cohere":
                    return self._call_cohere_api(texts)
                else:
                    raise ValueError(f"Unsupported provider: {self.provider}")
                    
            except Exception as e:
                last_error = e
                if attempt < API_RETRY_TIMES - 1:
                    wait_time = 2 ** attempt  # 指数退避
                    logger.warning(f"API call failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"API call failed after {API_RETRY_TIMES} attempts: {e}")
        
        raise last_error
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """获取文本的embedding向量"""
        if not texts:
            return []
        
        # 预处理文本
        processed_texts = []
        cache_keys = []
        cached_embeddings = {}
        
        for text in texts:
            # 截断过长文本
            processed_text = self._truncate_text(text.strip())
            processed_texts.append(processed_text)
            
            # 检查缓存
            cache_key = self._get_cache_key(processed_text)
            cache_keys.append(cache_key)
            
            cached_embedding = self._get_from_cache(cache_key)
            if cached_embedding:
                cached_embeddings[cache_key] = cached_embedding
        
        # 分离需要API调用的文本
        texts_to_call = []
        indices_to_call = []
        
        for i, (text, cache_key) in enumerate(zip(processed_texts, cache_keys)):
            if cache_key not in cached_embeddings:
                texts_to_call.append(text)
                indices_to_call.append(i)
        
        # 调用API获取新的embeddings
        new_embeddings = []
        if texts_to_call:
            logger.info(f"Calling {self.provider} API for {len(texts_to_call)} texts")
            new_embeddings = self._call_api_with_retry(texts_to_call)
            
            # 保存到缓存
            for i, embedding in enumerate(new_embeddings):
                cache_key = cache_keys[indices_to_call[i]]
                self._save_to_cache(cache_key, embedding)
        
        # 组合结果
        results = []
        new_embedding_index = 0
        
        for i, cache_key in enumerate(cache_keys):
            if cache_key in cached_embeddings:
                results.append(cached_embeddings[cache_key])
            else:
                results.append(new_embeddings[new_embedding_index])
                new_embedding_index += 1
        
        logger.info(f"Generated embeddings for {len(texts)} texts ({len(cached_embeddings)} from cache, {len(new_embeddings)} from API)")
        return results
    
    def get_single_embedding(self, text: str) -> List[float]:
        """获取单个文本的embedding向量"""
        embeddings = self.get_embeddings([text])
        return embeddings[0] if embeddings else []

# 全局实例
_embedding_service = None

def get_embedding_service() -> EmbeddingService:
    """获取embedding服务实例（单例模式）"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service

# 兼容性函数
def get_embeddings(texts: List[str]) -> List[List[float]]:
    """获取多个文本的embedding向量"""
    service = get_embedding_service()
    return service.get_embeddings(texts)

def get_single_embedding(text: str) -> List[float]:
    """获取单个文本的embedding向量"""
    service = get_embedding_service()
    return service.get_single_embedding(text) 