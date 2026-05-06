import json
import redis
from typing import Optional, Any
from app.core.config import settings

class CacheService:
    """Сервис для работы с Redis кешем"""
    
    def __init__(self):
        self.client = None
        self._connect()
    
    def _connect(self):
        """Подключение к Redis"""
        try:
            self.client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=5
            )
            self.client.ping()
            print("Redis connected successfully")
        except Exception as e:
            print(f"Redis connection failed: {e}")
            self.client = None
            
    def get_client(self):
        """Вернуть клиент Redis для прямых операций"""
        return self.client
    
    def is_available(self) -> bool:
        """Проверка доступности Redis"""
        return self.client is not None
    
    def get(self, key: str) -> Optional[Any]:
        """Получить значение из кеша"""
        if not self.is_available():
            return None
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception:
            return None
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Сохранить значение в кеш с TTL"""
        if not self.is_available():
            return False
        try:
            serialized = json.dumps(value, default=str)
            if ttl:
                self.client.setex(key, ttl, serialized)
            else:
                self.client.set(key, serialized)
            return True
        except Exception:
            return False
    
    def delete(self, key: str) -> bool:
        """Удалить ключ из кеша"""
        if not self.is_available():
            return False
        try:
            self.client.delete(key)
            return True
        except Exception:
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """Удалить все ключи по паттерну"""
        if not self.is_available():
            return 0
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception:
            return 0

# Глобальный экземпляр
cache_service = CacheService()