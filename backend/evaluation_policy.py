from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


EVALUATION_VERSION = "calendar-5d-next-session-v2"
MAX_SESSION_DELAY_DAYS = 7
MARKET_TIMEZONE = ZoneInfo("America/New_York")


def market_today() -> date:
    return datetime.now(MARKET_TIMEZONE).date()


def target_date(generated_at: datetime) -> date:
    if generated_at.tzinfo is None:
        raise ValueError("Evaluation requires a timezone-aware prediction timestamp.")
    return generated_at.astimezone(MARKET_TIMEZONE).date() + timedelta(days=5)


@dataclass(frozen=True)
class CloseObservation:
    session_date: date
    price: float
