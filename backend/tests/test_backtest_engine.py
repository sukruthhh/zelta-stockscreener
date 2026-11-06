from datetime import date, timedelta
from uuid import uuid4

import psycopg2
import pytest

import backtest_engine
from config import get_settings
from evaluation_policy import CloseObservation, EVALUATION_VERSION
from database import fetch_due_predictions, get_performance_summary


def test_grade_prediction_marks_correct_direction_and_low_error():
    prediction = {"id": 1, "ticker": "AAPL", "current_price": 100.0, "predicted_price": 110.0, "target_eval_date": date(2024, 1, 2)}
    result = backtest_engine.grade_prediction(prediction, fetch_price=lambda ticker, as_of: CloseObservation(as_of, 112.0))

    assert result is not None
    assert result.is_correct_direction is True
    assert result.absolute_error_pct == pytest.approx(2.0)  # |112-110|/100 * 100


def test_grade_prediction_marks_wrong_direction():
    # Model predicted a rise (110 > 100) but the stock actually fell.
    prediction = {"id": 2, "ticker": "MSFT", "current_price": 100.0, "predicted_price": 110.0, "target_eval_date": date(2024, 1, 2)}
    result = backtest_engine.grade_prediction(prediction, fetch_price=lambda ticker, as_of: CloseObservation(as_of, 95.0))

    assert result is not None
    assert result.is_correct_direction is False
    assert result.absolute_error_pct == pytest.approx(15.0)


def test_grade_prediction_returns_none_when_no_market_data_available():
    prediction = {"id": 3, "ticker": "NEWLY-LISTED", "current_price": 10.0, "predicted_price": 11.0, "target_eval_date": date.today()}
    result = backtest_engine.grade_prediction(prediction, fetch_price=lambda ticker, as_of: None)
    assert result is None


def _insert_due_prediction(ticker: str, *, current_price: float, predicted_price: float, days_ago: int = 5) -> int:
    with psycopg2.connect(get_settings().postgres_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO predictions (ticker, current_price, predicted_price, target_eval_date, model_version, result_status, evaluation_version)
            VALUES (%s, %s, %s, %s, 'deterministic-v1', 'complete', %s)
            RETURNING id
            """,
            (ticker, current_price, predicted_price, date.today() - timedelta(days=days_ago), EVALUATION_VERSION),
        )
        return cursor.fetchone()[0]


def test_run_grades_due_predictions_end_to_end(require_postgres):
    ticker = f"TEST{uuid4().hex[:6].upper()}"
    prediction_id = _insert_due_prediction(ticker, current_price=100.0, predicted_price=105.0)

    graded = backtest_engine.run(fetch_price=lambda t, as_of: CloseObservation(as_of, 108.0))

    graded_ids = {item.prediction_id for item in graded}
    assert prediction_id in graded_ids

    with psycopg2.connect(get_settings().postgres_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT is_evaluated, is_correct_direction, actual_close_price, actual_close_date, evaluation_version FROM predictions WHERE id = %s",
            (prediction_id,),
        )
        row = cursor.fetchone()
        assert row[0] is True
        assert row[1] is True
        assert float(row[2]) == pytest.approx(108.0)
        assert row[3] == date.today() - timedelta(days=5)
        assert row[4] == EVALUATION_VERSION


def test_run_skips_predictions_not_yet_due(require_postgres):
    ticker = f"TEST{uuid4().hex[:6].upper()}"
    future_id = _insert_due_prediction(ticker, current_price=50.0, predicted_price=55.0, days_ago=-2)

    graded = backtest_engine.run(fetch_price=lambda t, as_of: CloseObservation(as_of, 60.0))

    assert future_id not in {item.prediction_id for item in graded}


def test_unversioned_mock_predictions_are_ineligible(require_postgres):
    with psycopg2.connect(get_settings().postgres_url) as connection, connection.cursor() as cursor:
        cursor.execute("INSERT INTO predictions (ticker, current_price, predicted_price, target_eval_date) VALUES ('MOCK', 100, 110, '2024-01-02') RETURNING id")
        row_id = cursor.fetchone()[0]
    assert row_id not in {row["id"] for row in fetch_due_predictions(date.today())}


def test_old_grades_are_not_mixed_into_corrected_performance(require_postgres):
    before = get_performance_summary()
    row_id = _insert_due_prediction("LEGACY", current_price=100, predicted_price=110)
    with psycopg2.connect(get_settings().postgres_url) as connection, connection.cursor() as cursor:
        cursor.execute("UPDATE predictions SET is_evaluated=TRUE, is_correct_direction=TRUE, evaluation_version=NULL WHERE id=%s", (row_id,))
    after = get_performance_summary()
    assert after["evaluated_count"] == before["evaluated_count"]
    assert after["legacy_evaluated_count"] == before["legacy_evaluated_count"] + 1


def test_second_run_does_not_regrade_a_saved_result(require_postgres):
    row_id = _insert_due_prediction("ONCE", current_price=100, predicted_price=110)
    first = backtest_engine.run(fetch_price=lambda ticker, target: CloseObservation(target, 112))
    second = backtest_engine.run(fetch_price=lambda ticker, target: CloseObservation(target, 90))
    assert row_id in {row.prediction_id for row in first}
    assert row_id not in {row.prediction_id for row in second}


def test_pending_legacy_target_policy_is_not_silently_reinterpreted(require_postgres):
    row_id = _insert_due_prediction("OLDTARGET", current_price=100, predicted_price=110)
    before = get_performance_summary()
    with psycopg2.connect(get_settings().postgres_url) as connection, connection.cursor() as cursor:
        cursor.execute("UPDATE predictions SET evaluation_version=NULL WHERE id=%s", (row_id,))
    after = get_performance_summary()
    assert after["pending_count"] == before["pending_count"] - 1
    assert after["legacy_pending_count"] == before["legacy_pending_count"] + 1
    assert row_id not in {row["id"] for row in fetch_due_predictions(date.today())}
