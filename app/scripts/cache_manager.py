"""
Cache manager for large objects like LLM models and summarizers.

Provides efficient caching with LRU eviction and optional shared memory caching.
"""

import functools
import threading
import time
from typing import Any, Callable, Optional, Dict
from app.scripts.logger import setup_logger

logger = setup_logger(__name__)

# Thread-safe cache storage
_cache: Dict[str, Any] = {}
_cache_lock = threading.Lock()
_cache_timestamps: Dict[str, float] = {}


def cached(key: str, ttl: Optional[int] = None, max_size: int = 10):
    """
    Decorator for caching function results.
    
    Args:
        key: Cache key prefix
        ttl: Time-to-live in seconds (None = no expiration)
        max_size: Maximum number of cached items (LRU eviction)
    
    Usage:
        @cached("llm_model", ttl=3600)
        def get_llm_model():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.lru_cache(maxsize=max_size)
        def cached_func(*args, **kwargs):
            cache_key = f"{key}:{str(args)}:{str(kwargs)}"
            
            with _cache_lock:
                # Check TTL if set
                if ttl and cache_key in _cache_timestamps:
                    age = time.time() - _cache_timestamps[cache_key]
                    if age > ttl:
                        # Expired, remove from cache
                        if cache_key in _cache:
                            del _cache[cache_key]
                        del _cache_timestamps[cache_key]
                        logger.debug(f"Cache expired for {cache_key}")
                
                # Return cached value if exists
                if cache_key in _cache:
                    logger.debug(f"Cache hit for {cache_key}")
                    return _cache[cache_key]
            
            # Compute and cache result
            logger.debug(f"Cache miss for {cache_key}, computing...")
            result = func(*args, **kwargs)
            
            with _cache_lock:
                # Evict oldest if cache is full
                if len(_cache) >= max_size:
                    oldest_key = min(_cache_timestamps.items(), key=lambda x: x[1])[0]
                    del _cache[oldest_key]
                    del _cache_timestamps[oldest_key]
                    logger.debug(f"Evicted {oldest_key} from cache")
                
                _cache[cache_key] = result
                _cache_timestamps[cache_key] = time.time()
            
            return result
        
        # Preserve function metadata
        cached_func.__name__ = func.__name__
        cached_func.__doc__ = func.__doc__
        
        return cached_func
    return decorator


def get_cached(key: str) -> Optional[Any]:
    """Get a value from cache by key."""
    with _cache_lock:
        return _cache.get(key)


def set_cached(key: str, value: Any, ttl: Optional[int] = None):
    """Set a value in cache with optional TTL."""
    with _cache_lock:
        _cache[key] = value
        if ttl:
            _cache_timestamps[key] = time.time()
        else:
            _cache_timestamps[key] = 0  # No expiration


def clear_cache(key: Optional[str] = None):
    """
    Clear cache entries.
    
    Args:
        key: Specific key to clear (None = clear all)
    """
    with _cache_lock:
        if key:
            if key in _cache:
                del _cache[key]
            if key in _cache_timestamps:
                del _cache_timestamps[key]
            logger.info(f"Cleared cache for key: {key}")
        else:
            _cache.clear()
            _cache_timestamps.clear()
            logger.info("Cleared all cache")


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    with _cache_lock:
        return {
            'size': len(_cache),
            'keys': list(_cache.keys()),
            'oldest_age': min(_cache_timestamps.values()) if _cache_timestamps else 0,
            'newest_age': max(_cache_timestamps.values()) if _cache_timestamps else 0,
        }

