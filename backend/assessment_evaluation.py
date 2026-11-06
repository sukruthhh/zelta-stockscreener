"""Retrospective technical-only diagnostics, with identical observations for baselines."""
from datetime import date, datetime, time, timedelta, timezone
from random import Random

from analysis_engine import DeterministicAnalysisEngine
from evaluation_policy import EVALUATION_VERSION, MAX_SESSION_DELAY_DAYS, target_date


def evaluate_series(ticker: str, records: list[dict], *, seed: int = 31337, stride: int = 5) -> list[dict]:
    if stride < 1:
        raise ValueError("Stride must be positive.")
    rows = sorted(records, key=lambda row: row["date"])
    dates = [date.fromisoformat(row["date"]) for row in rows]
    if len(set(dates)) != len(dates):
        raise ValueError("Duplicate sessions must be resolved before evaluation.")
    engine = DeterministicAnalysisEngine()
    random = Random(seed)
    outcomes = []
    for index in range(engine.MINIMUM_SESSIONS - 1, len(rows), stride):
        generated = datetime.combine(dates[index], time(23), timezone.utc)
        # Pass only the prefix available at the signal close; no future news is used.
        result = engine.analyze(ticker, rows[:index + 1], now=generated)
        target = target_date(generated)
        observation = {
            "ticker": ticker, "signal_date": dates[index].isoformat(),
            "target_date": target.isoformat(), "assessment": result.assessment,
            "technical_score": result.technical_score, "model_version": result.model_version,
            "evaluation_version": EVALUATION_VERSION, "eligible": False,
        }
        outcomes.append(observation)
        later = next((j for j in range(index + 1, len(rows)) if dates[j] >= target), None)
        if later is None or dates[later] > target + timedelta(days=MAX_SESSION_DELAY_DAYS):
            observation["exclusion"] = "target_close_missing"
            continue
        if result.status in {"insufficient_data", "market_data_delayed", "failed"}:
            observation["exclusion"] = result.status
            continue
        if any(row.get("dividends", 0) or row.get("splits", 0) for row in rows[index + 1:later + 1]):
            observation["exclusion"] = "corporate_action_in_horizon"
            continue
        if result.assessment == "Neutral":
            observation["exclusion"] = "neutral_no_directional_call"
            continue
        entry, actual = float(result.indicators.current_price), float(rows[later]["close"])
        movement = 1 if actual > entry else -1 if actual < entry else 0
        predicted = 1 if result.assessment == "Bullish" else -1
        momentum = 1 if result.indicators.five_day_change_pct > 0 else -1 if result.indicators.five_day_change_pct < 0 else 0
        random_call = random.choice([-1, 1])
        observation.update({
            "eligible": True, "actual_close_date": dates[later].isoformat(),
            "entry_close": entry, "actual_close": actual, "actual_direction": movement,
            "model_correct": movement != 0 and predicted == movement,
            "momentum_call": momentum, "momentum_correct": movement != 0 and momentum == movement,
            "always_up_correct": movement == 1, "random_call": random_call,
            "random_correct": movement != 0 and random_call == movement,
        })
    return outcomes


def summarize(outcomes: list[dict]) -> dict:
    eligible = [row for row in outcomes if row["eligible"]]
    excluded = {}
    for row in outcomes:
        if not row["eligible"]:
            reason = row["exclusion"]
            excluded[reason] = excluded.get(reason, 0) + 1
    scores = {}
    for strategy in ("model", "momentum", "always_up", "random"):
        correct = sum(row[f"{strategy}_correct"] for row in eligible)
        scores[strategy] = {"correct": correct, "sample_size": len(eligible), "hit_rate": correct / len(eligible) if eligible else None}
    return {
        "candidate_count": len(outcomes), "eligible_count": len(eligible),
        "directional_call_count": sum(row["assessment"] != "Neutral" for row in outcomes),
        "directional_coverage": sum(row["assessment"] != "Neutral" for row in outcomes) / len(outcomes) if outcomes else None,
        "eligible_fraction": len(eligible) / len(outcomes) if outcomes else None,
        "exclusions": excluded, "strategies": scores,
        "interpretation": "Descriptive retrospective diagnostics, not trading returns, calibrated confidence, or statistical evidence of superiority. Overlapping/correlated observations and selected symbols limit generalization.",
    }
