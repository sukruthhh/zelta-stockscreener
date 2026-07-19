from datetime import datetime, timedelta, timezone

from analysis_engine import DeterministicAnalysisEngine


def market_records(prices: list[float], *, end: datetime | None = None) -> list[dict]:
    end = end or datetime.now(timezone.utc)
    records = []
    for index, price in enumerate(prices):
        date = end - timedelta(days=len(prices) - index - 1)
        records.append(
            {
                "date": date.date().isoformat(),
                "open": price - 0.25,
                "high": price + 1,
                "low": price - 1,
                "close": price,
                "volume": 2_000_000 if index == len(prices) - 1 else 1_000_000,
            }
        )
    return records


def test_rising_market_is_bullish():
    prices = [100 + (index * 0.75) for index in range(70)]

    result = DeterministicAnalysisEngine().analyze("aapl", market_records(prices))

    assert result.assessment == "Bullish"
    assert result.technical_score >= 0.25
    assert result.status == "news_unavailable"
    assert result.risk_range.lower < result.indicators.current_price < result.risk_range.upper
    assert result.sources == []
    assert "News sentiment" in result.warnings[0]


def test_falling_market_is_bearish():
    prices = [160 - (index * 0.75) for index in range(70)]

    result = DeterministicAnalysisEngine().analyze("MSFT", market_records(prices))

    assert result.assessment == "Bearish"
    assert result.technical_score <= -0.25


def test_flat_market_is_neutral():
    prices = [100.0 for _ in range(70)]

    result = DeterministicAnalysisEngine().analyze("NVDA", market_records(prices))

    assert result.assessment == "Neutral"
    assert result.technical_score == 0


def test_insufficient_data_does_not_generate_an_assessment():
    result = DeterministicAnalysisEngine().analyze(
        "TSLA",
        market_records([100 + index for index in range(20)]),
    )

    assert result.status == "insufficient_data"
    assert result.assessment == "Neutral"
    assert result.confidence == 0
    assert result.indicators.current_price is None


def test_stale_data_is_visible_in_the_result():
    now = datetime.now(timezone.utc)
    prices = [100 + (index * 0.5) for index in range(70)]

    result = DeterministicAnalysisEngine().analyze(
        "AMD",
        market_records(prices, end=now - timedelta(days=10)),
        now=now,
    )

    assert result.status == "market_data_delayed"
    assert result.confidence < 0.75
    assert "10 days old" in result.warnings[0]
