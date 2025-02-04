from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional, TypeVar, Generic, Callable
from datetime import datetime, timedelta
import logging
from functools import wraps

log = logging.getLogger(__name__)

T = TypeVar('T')

class Cache(Generic[T]):
    """A simple cache implementation with TTL support."""
    
    def __init__(self, ttl: int = 300):
        self.ttl = ttl
        self.cache: Dict[str, tuple[T, datetime]] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

    def __call__(self, key: str) -> Callable:
        """Decorator for caching function results."""
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> T:
                cache_key = f"{key}:{args}:{kwargs}"
                
                if cache_key in self.cache:
                    value, timestamp = self.cache[cache_key]
                    if datetime.now() < timestamp + timedelta(seconds=self.ttl):
                        return value
                
                value = await func(*args, **kwargs)
                self.cache[cache_key] = (value, datetime.now())
                return value
                
            return wrapper
        return decorator

    async def cleanup(self) -> None:
        """Remove expired cache entries."""
        while True:
            now = datetime.now()
            expired_keys = [
                key for key, (_, timestamp) in self.cache.items()
                if now > timestamp + timedelta(seconds=self.ttl)
            ]
            
            for key in expired_keys:
                del self.cache[key]
                
            await asyncio.sleep(60)  

    def start_cleanup(self) -> None:
        """Start the cleanup task."""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self.cleanup())

    def stop_cleanup(self) -> None:
        """Stop the cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None

def cache(bot: Any) -> Cache:
    """Create and start a new cache instance."""
    cache_instance = Cache()
    cache_instance.start_cleanup()
    return cache_instance 