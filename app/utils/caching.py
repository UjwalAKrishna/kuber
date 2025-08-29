import hashlib
import json
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class CacheEntry:
    data: Any
    timestamp: float
    ttl: float
    
    def is_expired(self) -> bool:
        return time.time() > (self.timestamp + self.ttl)


class SimpleCache:
    """Simple in-memory cache for voice queries."""
    
    def __init__(self, default_ttl: float = 300.0):  # 5 minutes default
        self.cache: Dict[str, CacheEntry] = {}
        self.default_ttl = default_ttl
        self.max_size = 1000  # Prevent memory bloat
    
    def _generate_key(self, audio_bytes: bytes, session_id: str = "") -> str:
        """Generate cache key from audio content and session."""
        audio_hash = hashlib.md5(audio_bytes).hexdigest()
        return f"{session_id}:{audio_hash}"
    
    def get(self, audio_bytes: bytes, session_id: str = "") -> Optional[Dict[str, Any]]:
        """Get cached result for audio query."""
        key = self._generate_key(audio_bytes, session_id)
        
        if key in self.cache:
            entry = self.cache[key]
            if not entry.is_expired():
                return entry.data
            else:
                # Remove expired entry
                del self.cache[key]
        
        return None
    
    def set(self, audio_bytes: bytes, result: Dict[str, Any], session_id: str = "", ttl: Optional[float] = None) -> None:
        """Cache result for audio query."""
        if ttl is None:
            ttl = self.default_ttl
        
        key = self._generate_key(audio_bytes, session_id)
        
        # Implement simple LRU by removing oldest entries if cache is full
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k].timestamp)
            del self.cache[oldest_key]
        
        self.cache[key] = CacheEntry(
            data=result,
            timestamp=time.time(),
            ttl=ttl
        )
    
    def clear(self) -> None:
        """Clear all cached entries."""
        self.cache.clear()
    
    def cleanup_expired(self) -> int:
        """Remove expired entries and return count of removed items."""
        expired_keys = [
            key for key, entry in self.cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        return len(expired_keys)
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        expired_count = sum(1 for entry in self.cache.values() if entry.is_expired())
        
        return {
            "total_entries": len(self.cache),
            "expired_entries": expired_count,
            "active_entries": len(self.cache) - expired_count,
            "max_size": self.max_size,
            "default_ttl": self.default_ttl
        }


# Global cache instance
voice_cache = SimpleCache()