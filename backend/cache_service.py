import os
import json
from datetime import datetime, time, timedelta, timezone
from typing import Optional, Any
from zoneinfo import ZoneInfo
import redis
from dotenv import load_dotenv

load_dotenv()

MARKET_TIMEZONE = ZoneInfo("America/New_York")


def intraday_ttl_seconds(now: datetime | None = None) -> int:
    """Bound cache residence using a conservative daily 04:00–16:00 New York window.

    This is not an exchange calendar or a guarantee of upstream quote freshness.
    Short TTLs also apply on weekends/holidays rather than extending stale entries.
    """
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise ValueError("Cache policy requires a timezone-aware timestamp.")
    local = current.astimezone(MARKET_TIMEZONE)
    if time(4) <= local.time() < time(16):
        return 15

    next_date = local.date() if local.time() < time(4) else local.date() + timedelta(days=1)
    next_active = datetime.combine(next_date, time(4), tzinfo=MARKET_TIMEZONE)
    until_active = (next_active.astimezone(timezone.utc) - current.astimezone(timezone.utc)).total_seconds()
    return max(1, min(43200, int(until_active)))


class RedisCacheService:
    def __init__(self):
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.pool = redis.ConnectionPool.from_url(redis_url, decode_responses=True)

    @property
    def client(self):
        return redis.Redis(connection_pool=self.pool)

    def get_cached_feed(self, key: str) -> Optional[Any]:
        try:
            data = self.client.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            print(f"Redis Read Error: {e}")
        return None

    # Base low-level setter
    def set_market_feed(self, key: str, data: Any, ttl_seconds: int):
        try:
            serialized_data = json.dumps(data)
            self.client.setex(key, ttl_seconds, serialized_data)
        except Exception as e:
            print(f"Redis Write Error: {e}")

    # =====================================================================
    # STRATEGIC MARKET TTL WRAPPERS
    # =====================================================================

    def cache_intraday_ticker(self, symbol: str, data: Any):
        """Intraday shifts rapidly. Cache for only 15 seconds during market hours."""
        key = f"ticker:live:{symbol.upper()}"
        self.set_market_feed(key, data, ttl_seconds=15)

    def cache_intraday_ticker_smart(self, symbol: str, data: Any):
        """Expire overnight entries by the next 04:00 New York boundary."""
        key = f"ticker:live:{symbol.upper()}"
        self.set_market_feed(key, data, ttl_seconds=intraday_ttl_seconds())

    def cache_historical_timeline(self, symbol: str, data: Any):
        """Historical data (EOD) changes daily. Cache for 1 hour (3600s)."""
        key = f"ticker:history:{symbol.upper()}"
        self.set_market_feed(key, data, ttl_seconds=3600)

    def cache_morning_alerts(self, data: Any):
        """Heavy calculations. Keep the generated batch alerts clean for 15 minutes (900s)."""
        key = "screener:morning:matched"
        self.set_market_feed(key, data, ttl_seconds=900)

    def cache_news_feed(self, symbol: str, data: Any):
        """News updates steadily. Hold context for 30 minutes (1800s)."""
        key = f"news:feed:{symbol.upper()}"
        self.set_market_feed(key, data, ttl_seconds=1800)

# Global instance to import across endpoints
market_cache = RedisCacheService()
