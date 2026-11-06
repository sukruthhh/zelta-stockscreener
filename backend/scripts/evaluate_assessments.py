"""Fetch a price snapshot once, then replay it offline. Never touches product databases."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path

from assessment_evaluation import evaluate_series, summarize


def fetch_snapshot(path: Path, tickers: list[str], start: str, end: str) -> dict:
    import yfinance as yf

    snapshot = {
        "source": "Yahoo Finance through yfinance", "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "start": start, "end_exclusive": end, "auto_adjust": True, "tickers": {}, "failures": [],
    }
    for ticker in tickers:
        try:
            frame = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=True, timeout=15)
            if frame.empty:
                raise ValueError("No price records returned")
            snapshot["tickers"][ticker] = [{
                "date": timestamp.date().isoformat(), "open": float(row["Open"]),
                "high": float(row["High"]), "low": float(row["Low"]), "close": float(row["Close"]),
                "volume": int(row["Volume"]), "dividends": float(row.get("Dividends", 0)),
                "splits": float(row.get("Stock Splits", 0)),
            } for timestamp, row in frame.iterrows()]
        except Exception as exc:
            snapshot["failures"].append({"ticker": ticker, "type": type(exc).__name__, "error": str(exc)})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--tickers", nargs="+", default=["AAPL", "MSFT", "SPY"])
    parser.add_argument("--start", default="2024-01-01")
    parser.add_argument("--end", default="2026-01-01")
    parser.add_argument("--seed", type=int, default=31337)
    parser.add_argument("--stride", type=int, default=5)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; choose a new path to retain previous trials.")
    if args.fetch:
        if args.snapshot.exists():
            parser.error("Snapshot already exists; choose a new path to retain previous trials.")
        snapshot = fetch_snapshot(args.snapshot, args.tickers, args.start, args.end)
    else:
        snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    outcomes = []
    evaluation_failures = []
    for ticker, records in snapshot["tickers"].items():
        try:
            outcomes.extend(evaluate_series(ticker, records, seed=args.seed, stride=args.stride))
        except Exception as exc:
            evaluation_failures.append({"ticker": ticker, "type": type(exc).__name__, "error": str(exc)})
    artifact = {
        "source_revision": os.getenv("ZELTA_SOURCE_REVISION", "unrecorded"),
        "snapshot_sha256": sha256(args.snapshot.read_bytes()).hexdigest(),
        "source": snapshot["source"], "downloaded_at": snapshot["downloaded_at"],
        "start": snapshot["start"], "end_exclusive": snapshot["end_exclusive"],
        "rows_per_ticker": {ticker: len(rows) for ticker, rows in snapshot["tickers"].items()},
        "download_failures": snapshot["failures"], "seed": args.seed, "stride": args.stride,
        "evaluation_failures": evaluation_failures,
        "conditions": "Technical-only, adjusted daily snapshot; no historical news, costs, executable entry assumptions or prospective holdout. Model weights were not tuned in this experiment. Adjustments are current-vintage, not point-in-time data.",
        "summary": summarize(outcomes), "observations": outcomes,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"rows_per_ticker": artifact["rows_per_ticker"], "download_failures": artifact["download_failures"], "summary": artifact["summary"]}, indent=2))
    return 1 if snapshot["failures"] or evaluation_failures or not outcomes else 0


if __name__ == "__main__":
    raise SystemExit(main())
