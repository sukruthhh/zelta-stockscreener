"""Grade eligible saved calls against dated, completed yfinance sessions.

Targets use five calendar days from generation in New York. Wait until a session
is complete and select the first provided close on/after the target, bounded to
seven further days. Run manually from backend: python backtest_engine.py.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from math import isfinite
from typing import Callable

import yfinance as yf

from database import fetch_due_predictions, record_backtest_result
from config import get_settings
from evaluation_policy import CloseObservation, EVALUATION_VERSION, MAX_SESSION_DELAY_DAYS, market_today

logger = logging.getLogger(__name__)

PriceFetcher = Callable[[str, date], CloseObservation | None]


@dataclass(frozen=True)
class GradedPrediction:
    prediction_id: int
    ticker: str
    actual_close_price: float
    actual_close_date: date
    absolute_error_pct: float
    is_correct_direction: bool
    evaluation_version: str = EVALUATION_VERSION


def _default_price_fetcher(ticker: str, as_of: date) -> CloseObservation | None:
    """First provided completed session on/after target, at most seven days later."""
    today = market_today()
    if as_of >= today:
        return None
    end = min(today, as_of + timedelta(days=MAX_SESSION_DELAY_DAYS + 1))
    history = yf.Ticker(ticker).history(
        start=as_of.isoformat(), end=end.isoformat(), auto_adjust=True,
        timeout=get_settings().market_data_timeout_seconds,
    )
    if history.empty:
        return None
    for timestamp, row in history.sort_index().iterrows():
        session = timestamp.date()
        if as_of <= session < end:
            price = float(row["Close"])
            return CloseObservation(session, price) if isfinite(price) and price > 0 else None
    return None


def grade_prediction(prediction: dict, *, fetch_price: PriceFetcher, as_of: date | None = None) -> GradedPrediction | None:
    """Returns None (rather than raising) when market data isn't available
    yet -- the prediction is simply left unevaluated and picked up on a
    later run, instead of the whole batch failing over one bad ticker."""
    current_price = float(prediction["current_price"])
    predicted_price = float(prediction["predicted_price"])
    if not all(isfinite(value) and value > 0 for value in (current_price, predicted_price)) or predicted_price == current_price:
        return None
    target = prediction["target_eval_date"]
    today = as_of or market_today()
    if target >= today:
        return None
    observation = fetch_price(prediction["ticker"], target)
    if not isinstance(observation, CloseObservation):
        return None
    if not target <= observation.session_date <= target + timedelta(days=MAX_SESSION_DELAY_DAYS) or observation.session_date >= today:
        return None
    actual_close_price = observation.price
    if not isfinite(actual_close_price) or actual_close_price <= 0:
        return None

    # Error is expressed as a percentage of the price at prediction time,
    # not of the (possibly near-zero) predicted move -- that keeps the
    # metric stable and comparable across tickers of very different prices.
    absolute_error_pct = round(abs(actual_close_price - predicted_price) / current_price * 100, 2)

    return GradedPrediction(
        prediction_id=prediction["id"],
        ticker=prediction["ticker"],
        actual_close_price=actual_close_price,
        actual_close_date=observation.session_date,
        absolute_error_pct=absolute_error_pct,
        is_correct_direction=(predicted_price - current_price) * (actual_close_price - current_price) > 0,
    )


def run(*, fetch_price: PriceFetcher = _default_price_fetcher, as_of: date | None = None) -> list[GradedPrediction]:
    today = as_of or market_today()
    due = fetch_due_predictions(as_of=today)
    graded: list[GradedPrediction] = []
    for prediction in due:
        try:
            result = grade_prediction(prediction, fetch_price=fetch_price, as_of=today)
        except Exception:
            logger.exception("Prediction %s could not be graded; continuing batch.", prediction["id"])
            continue
        if result is None:
            continue
        saved = record_backtest_result(
            result.prediction_id,
            actual_close_price=result.actual_close_price,
            actual_close_date=result.actual_close_date,
            evaluation_version=result.evaluation_version,
            absolute_error_pct=result.absolute_error_pct,
            is_correct_direction=result.is_correct_direction,
        )
        if saved:
            graded.append(result)
    return graded


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = run()
    print(f"Evaluated {len(results)} prediction(s) due for grading.")
    for item in results:
        verdict = "correct" if item.is_correct_direction else "wrong"
        print(
            f"  {item.ticker}: {verdict} direction, "
            f"{item.absolute_error_pct}% off target (actual close {item.actual_close_price})"
        )
