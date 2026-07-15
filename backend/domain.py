import json
import re


TICKER_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9.-]{0,9}$")
ASSESSMENTS = {"bullish", "neutral", "bearish"}


def normalize_ticker(value: str) -> str:
    normalized = value.strip().upper()
    if not TICKER_PATTERN.fullmatch(normalized):
        raise ValueError("Ticker may contain only letters, numbers, dots, and hyphens.")
    return normalized


def morning_screener_cache_key(tickers: list[str], threshold: float) -> str:
    normalized = sorted({normalize_ticker(ticker) for ticker in tickers})
    return f"screener:morning:{','.join(normalized)}:{threshold:g}"


def parse_assessment(raw_output: str) -> tuple[str, dict]:
    cleaned = raw_output.strip().removeprefix("```json").removesuffix("```").strip()
    parsed = json.loads(cleaned)
    assessment = str(parsed["final_bias"]).lower()
    if assessment not in ASSESSMENTS:
        raise ValueError("Unsupported assessment")
    return assessment, parsed

