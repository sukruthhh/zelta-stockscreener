"""Replay HTTP requests with real Redis and fixture prices, never live provider calls.

Run only via compose.test.yml; output records every request, failure, and condition.
This estimates neither production cache hit rate nor live market-data latency.
"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
from statistics import median
from time import perf_counter
from unittest.mock import patch

from fastapi.testclient import TestClient
import pandas as pd

import main
from cache_service import intraday_ttl_seconds


TICKERS = ["ZBENCHA", "ZBENCHB", "ZBENCHC", "ZBENCHD", "ZBENCHE"]
PRICES = {ticker: 100.0 + index for index, ticker in enumerate(TICKERS)}


def run_replay(output: Path) -> dict:
    if os.getenv("ZELTA_ISOLATED_TEST") != "1" or os.getenv("REDIS_URL") != "redis://test-redis:6379/0":
        raise RuntimeError("Run this replay in compose.test.yml's isolated test environment.")
    main.market_cache.client.ping()
    keys = [f"ticker:live:{ticker}" for ticker in TICKERS]
    artifact = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "conditions": {
            "endpoint": "GET /api/v1/test-ticker/{symbol}",
            "http_transport": "in-process FastAPI TestClient (not network or browser)",
            "redis": "real isolated Redis 7; no persisted data",
            "market_data": "fixture closes; no artificial network delay; no live or paid provider calls",
            "workload": "3 rounds, each with 100 uncached + 100 cached requests; 5 symbols repeated 20 times",
            "cache_policy": "actual wall-clock policy, including cold misses in cached runs",
            "source_revision": os.getenv("ZELTA_SOURCE_REVISION", "unrecorded"),
            "limitations": "Designed repetition is not production demand. Latency excludes upstream network and browser polling.",
        },
        "rounds": [], "requests": [], "failures": [],
    }
    calls = 0

    class FixtureTicker:
        def __init__(self, ticker):
            self.ticker = ticker

        def history(self, **kwargs):
            nonlocal calls
            calls += 1
            return pd.DataFrame({"Close": [PRICES[self.ticker]]})

    try:
        # Startup uses the isolated DB; the measured endpoint uses Redis/provider only.
        with TestClient(main.app) as client, patch.object(main.yf, "Ticker", FixtureTicker):
            for round_number in range(1, 4):
                for mode in ("uncached", "cached"):
                    main.market_cache.client.delete(*keys)
                    calls = 0
                    durations = []
                    hits = 0
                    start = perf_counter()
                    bypass = patch.object(main.market_cache, "get_cached_feed", return_value=None) if mode == "uncached" else nullcontext()
                    with bypass:
                        for index in range(100):
                            ticker = TICKERS[index % len(TICKERS)]
                            request_start = perf_counter()
                            response = client.get(f"/api/v1/test-ticker/{ticker}")
                            elapsed_ms = (perf_counter() - request_start) * 1000
                            body = response.json()
                            correct = response.status_code == 200 and body.get("live_price") == PRICES[ticker]
                            durations.append(elapsed_ms)
                            hits += body.get("source") == "cache"
                            artifact["requests"].append({
                                "round": round_number, "mode": mode, "index": index, "ticker": ticker,
                                "elapsed_ms": elapsed_ms, "status": response.status_code,
                                "source": body.get("source"), "payload_correct": correct,
                            })
                            if not correct:
                                raise AssertionError(f"Unexpected payload for {ticker}")
                    elapsed = perf_counter() - start
                    # Keep the workload within the minimum configured TTL so expiry cannot confound hit counts.
                    if elapsed >= 15 or intraday_ttl_seconds() < 15:
                        raise AssertionError("Replay crossed its cache timing boundary; repeat away from 04:00 New York.")
                    expected_calls = 100 if mode == "uncached" else 5
                    if calls != expected_calls:
                        raise AssertionError(f"Expected {expected_calls} upstream fixture calls; observed {calls}")
                    artifact["rounds"].append({
                        "round": round_number, "mode": mode, "requests": 100,
                        "cache_hits": hits, "cache_hit_rate": hits / 100,
                        "upstream_fixture_calls": calls,
                        "median_http_ms": median(durations),
                        "p95_http_ms": sorted(durations)[94],
                        "elapsed_seconds": elapsed,
                        "remaining_redis_ttls": [main.market_cache.client.ttl(key) for key in keys],
                    })
    except Exception as exc:
        artifact["failures"].append({"type": type(exc).__name__, "message": str(exc)})
        raise
    finally:
        try:
            main.market_cache.client.delete(*keys)
        except Exception as exc:
            artifact["failures"].append({"type": type(exc).__name__, "message": "Test-key cleanup failed."})
        artifact["finished_at"] = datetime.now(timezone.utc).isoformat()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    return artifact


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_replay(args.output)
    print(json.dumps({"rounds": result["rounds"], "failures": result["failures"]}, indent=2))
