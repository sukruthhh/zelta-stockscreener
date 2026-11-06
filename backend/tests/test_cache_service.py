from datetime import datetime
from uuid import uuid4

import pytest
import redis

from cache_service import RedisCacheService, intraday_ttl_seconds


@pytest.mark.parametrize(("timestamp", "ttl"), [
    ("2026-11-06T08:59:59+00:00", 1),
    ("2026-11-06T09:00:00+00:00", 15),
    ("2026-11-06T20:59:59+00:00", 15),
    ("2026-11-06T21:00:00+00:00", 43200),
    ("2026-11-06T23:00:00+00:00", 36000),
    ("2026-11-07T08:30:00+00:00", 1800),
    ("2026-07-10T07:59:50+00:00", 10),
    ("2026-03-08T05:00:00+00:00", 10800),
    ("2026-11-01T04:00:00+00:00", 18000),
])
def test_intraday_ttl_respects_new_york_boundaries_and_dst(timestamp, ttl):
    assert intraday_ttl_seconds(datetime.fromisoformat(timestamp)) == ttl


def test_policy_does_not_depend_on_callers_timezone():
    utc = datetime.fromisoformat("2026-11-06T08:30:00+00:00")
    other_zone = datetime.fromisoformat("2026-11-06T17:30:00+09:00")
    assert intraday_ttl_seconds(utc) == intraday_ttl_seconds(other_zone) == 1800


def test_naive_time_is_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        intraday_ttl_seconds(datetime(2026, 11, 6, 3, 30))


def test_smart_cache_writes_the_bounded_ttl(monkeypatch):
    cache = RedisCacheService()
    writes = []
    monkeypatch.setattr("cache_service.intraday_ttl_seconds", lambda: 1)
    monkeypatch.setattr(cache, "set_market_feed", lambda key, data, ttl_seconds: writes.append((key, ttl_seconds)))
    cache.cache_intraday_ticker_smart("aapl", {"live_price": 100})
    assert writes == [("ticker:live:AAPL", 1)]


def test_real_redis_round_trip_and_expiration():
    cache = RedisCacheService()
    try:
        cache.client.ping()
    except redis.RedisError:
        pytest.skip("No reachable Redis; run the isolated compose test environment.")
    key = f"test:cache:{uuid4()}"
    try:
        cache.set_market_feed(key, {"live_price": 100}, ttl_seconds=15)
        assert cache.get_cached_feed(key) == {"live_price": 100}
        assert 0 < cache.client.ttl(key) <= 15
        # Explicitly expire this isolated key; no wall-clock sleep or shared-data deletion.
        cache.client.expire(key, 0)
        assert cache.get_cached_feed(key) is None
    finally:
        cache.client.delete(key)
