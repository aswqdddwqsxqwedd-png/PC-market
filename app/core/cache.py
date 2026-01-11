"""Сервис кеширования Redis для часто используемых данных."""
import json
import structlog
from typing import Optional, Any
from redis.asyncio import Redis, ConnectionPool
from app.core.config import settings

logger = structlog.get_logger(__name__)

# Глобальный пул соединений Redis
_redis_pool: Optional[ConnectionPool] = None
_redis_client: Optional[Redis] = None


async def get_redis() -> Optional[Redis]:
    """
    Получить экземпляр клиента Redis.
    
    Returns:
        Клиент Redis или None, если Redis отключен или недоступен
    """
    global _redis_client, _redis_pool
    
    if not settings.redis_enabled:
        return None
    
    if _redis_client is None:
        try:
            _redis_pool = ConnectionPool.from_url(
                settings.redis_url,
                decode_responses=True,
                max_connections=10
            )
            _redis_client = Redis(connection_pool=_redis_pool)
            # Проверка соединения
            await _redis_client.ping()
            logger.info("redis_connected", url=settings.redis_url)
        except Exception as e:
            logger.warning("redis_connection_failed", error=str(e))
            _redis_client = None
            return None
    
    return _redis_client


async def close_redis() -> None:
    """Закрыть пул соединений Redis."""
    global _redis_client, _redis_pool
    
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
    
    if _redis_pool:
        await _redis_pool.disconnect()
        _redis_pool = None
    
    logger.info("redis_disconnected")


async def get_cache(key: str) -> Optional[Any]:
    """
    Получить значение из кеша.
    
    Args:
        key: Ключ кеша
        
    Returns:
        Значение из кеша или None, если не найдено
    """
    redis = await get_redis()
    if not redis:
        return None
    
    try:
        value = await redis.get(key)
        if value:
            return json.loads(value)
    except Exception as e:
        logger.warning("cache_get_error", key=key, error=str(e))
    
    return None


async def set_cache(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """
    Установить значение в кеш.
    
    Args:
        key: Ключ кеша
        value: Значение для кеширования (должно быть JSON-сериализуемым)
        ttl: Время жизни в секундах (по умолчанию settings.cache_ttl)
        
    Returns:
        True при успехе, False в противном случае
    """
    redis = await get_redis()
    if not redis:
        return False
    
    try:
        ttl = ttl or settings.cache_ttl
        serialized = json.dumps(value)
        await redis.setex(key, ttl, serialized)
        return True
    except Exception as e:
        logger.warning("cache_set_error", key=key, error=str(e))
        return False


async def delete_cache(key: str) -> bool:
    """
    Удалить значение из кеша.
    
    Args:
        key: Ключ кеша
        
    Returns:
        True при успехе, False в противном случае
    """
    redis = await get_redis()
    if not redis:
        return False
    
    try:
        await redis.delete(key)
        return True
    except Exception as e:
        logger.warning("cache_delete_error", key=key, error=str(e))
        return False


async def invalidate_pattern(pattern: str) -> int:
    """
    Инвалидировать все ключи кеша, соответствующие паттерну.
    
    Args:
        pattern: Паттерн Redis (например, "user:*", "item:*")
        
    Returns:
        Количество удаленных ключей
    """
    redis = await get_redis()
    if not redis:
        return 0
    
    try:
        keys = []
        async for key in redis.scan_iter(match=pattern):
            keys.append(key)
        
        if keys:
            await redis.delete(*keys)
        
        return len(keys)
    except Exception as e:
        logger.warning("cache_invalidate_error", pattern=pattern, error=str(e))
        return 0

