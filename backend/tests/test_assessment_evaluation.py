from copy import deepcopy
from datetime import date, datetime, timedelta, timezone

import pytest

from assessment_evaluation import evaluate_series, summarize
from evaluation_policy import CloseObservation, target_date
from backtest_engine import grade_prediction


def records(count=130):
    start = date(2024, 1, 2)
    rows = []
    day = start
    while len(rows) < count:
        if day.weekday() < 5:
            price = 100 + len(rows) * 0.5
            rows.append(dict(date=day.isoformat(), open=price, high=price + 1, low=price - 1, close=price, volume=1000000))
        day += timedelta(days=1)
    return rows


def test_historical_comparisons_share_denominators_and_reproduce_random_calls():
    first = evaluate_series("TEST", records())
    assert first == evaluate_series("TEST", records())
    summary = summarize(first)
    assert summary["eligible_count"] > 0
    assert {score["sample_size"] for score in summary["strategies"].values()} == {summary["eligible_count"]}
    assert summary["strategies"]["model"]["hit_rate"] == 1  # synthetic rising path, not real performance


def test_future_prices_cannot_change_earlier_model_calls():
    original = records()
    changed = deepcopy(original)
    for row in changed[90:]:
        row["close"] *= 0.1
        row["high"] = row["close"] + 1
        row["low"] = row["close"] - 1
    cutoff = original[90]["date"]
    before = [(row["signal_date"], row["assessment"], row["technical_score"]) for row in evaluate_series("TEST", original) if row["signal_date"] < cutoff]
    after = [(row["signal_date"], row["assessment"], row["technical_score"]) for row in evaluate_series("TEST", changed) if row["signal_date"] < cutoff]
    assert before == after


def test_neutral_calls_are_retained_as_exclusions():
    series = records()
    for row in series:
        row.update(close=100, high=101, low=99)
    summary = summarize(evaluate_series("FLAT", series))
    assert summary["eligible_count"] == 0
    assert summary["exclusions"]["neutral_no_directional_call"] > 0
    assert summary["strategies"]["model"]["hit_rate"] is None


def test_calendar_target_uses_new_york_generation_date():
    assert target_date(datetime(2026, 11, 7, 1, tzinfo=timezone.utc)) == date(2026, 11, 11)


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf")])
def test_invalid_close_is_not_graded(value):
    row = dict(id=1, ticker="TEST", current_price=100, predicted_price=110, target_eval_date=date(2024, 1, 2))
    assert grade_prediction(row, fetch_price=lambda *args: CloseObservation(date(2024, 1, 2), value)) is None


def test_undated_close_is_not_accepted():
    row = dict(id=1, ticker="TEST", current_price=100, predicted_price=110, target_eval_date=date(2024, 1, 2))
    assert grade_prediction(row, fetch_price=lambda *args: 110) is None


@pytest.mark.parametrize("session", [date(2024, 1, 1), date(2024, 1, 10), date(2024, 1, 20)])
def test_dated_close_must_be_completed_and_within_the_bound(session):
    row = dict(id=1, ticker="TEST", current_price=100, predicted_price=110, target_eval_date=date(2024, 1, 2))
    assert grade_prediction(row, fetch_price=lambda *args: CloseObservation(session, 110), as_of=date(2024, 1, 20)) is None
