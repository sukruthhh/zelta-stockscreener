from datetime import date

import pandas as pd
import pytest

import backtest_engine as engine
from evaluation_policy import CloseObservation


def patch_history(monkeypatch, frames):
    calls = []

    class Ticker:
        def history(self, **kwargs):
            calls.append(kwargs)
            return frames[min(len(calls) - 1, len(frames) - 1)]

    monkeypatch.setattr(engine.yf, "Ticker", lambda ticker: Ticker())
    return calls


def close_frame(dates, prices):
    return pd.DataFrame({"Close": prices}, index=pd.to_datetime(dates, utc=True))


def close_value(result):
    return result.price if hasattr(result, "price") else result


def test_fetch_uses_first_target_session_not_last_returned_close(monkeypatch):
    patch_history(monkeypatch, [close_frame(["2024-01-02", "2024-01-03", "2024-01-08"], [101, 95, 999])])
    result = engine._default_price_fetcher("AAPL", date(2024, 1, 2))
    assert close_value(result) == 101


def test_weekend_target_uses_next_provided_completed_session(monkeypatch):
    patch_history(monkeypatch, [close_frame(["2024-01-08", "2024-01-09"], [108, 109])])
    result = engine._default_price_fetcher("AAPL", date(2024, 1, 6))
    assert result == CloseObservation(date(2024, 1, 8), 108)


def test_empty_target_window_does_not_fall_back_to_recent_unrelated_prices(monkeypatch):
    calls = patch_history(monkeypatch, [pd.DataFrame(), close_frame(["2026-01-01"], [999])])
    assert engine._default_price_fetcher("AAPL", date(2024, 1, 2)) is None
    assert len(calls) == 1


def test_fetch_rejects_rows_outside_the_target_window(monkeypatch):
    patch_history(monkeypatch, [close_frame(["2023-12-29", "2024-02-01"], [10, 999])])
    assert engine._default_price_fetcher("AAPL", date(2024, 1, 2)) is None


def test_today_is_not_treated_as_a_completed_daily_session(monkeypatch):
    today = engine.date.today()
    patch_history(monkeypatch, [close_frame([today.isoformat()], [999])])
    assert engine._default_price_fetcher("AAPL", today) is None


def test_unchanged_price_is_not_a_correct_bearish_call():
    prediction = {"id": 1, "ticker": "AAPL", "current_price": 100, "predicted_price": 90, "target_eval_date": date(2024, 1, 2)}
    result = engine.grade_prediction(prediction, fetch_price=lambda ticker, target: CloseObservation(target, 100))
    assert result is not None
    assert result.is_correct_direction is False


def test_bad_entry_price_is_not_graded():
    prediction = {"id": 1, "ticker": "AAPL", "current_price": 0, "predicted_price": 90, "target_eval_date": date(2024, 1, 2)}
    assert engine.grade_prediction(prediction, fetch_price=lambda *args: 100) is None


def test_one_provider_failure_does_not_abort_the_rest_of_the_batch(monkeypatch):
    predictions = [dict(id=i, ticker=ticker, current_price=100, predicted_price=110, target_eval_date=date(2024, 1, 2)) for i, ticker in [(1, "BAD"), (2, "GOOD")]]
    monkeypatch.setattr(engine, "fetch_due_predictions", lambda **kwargs: predictions)
    monkeypatch.setattr(engine, "record_backtest_result", lambda *args, **kwargs: True)

    def fetch(ticker, target):
        if ticker == "BAD":
            raise RuntimeError("provider unavailable")
        return CloseObservation(target, 110)

    assert [row.prediction_id for row in engine.run(fetch_price=fetch)] == [2]
