# generate_mock_predictions.py
import os
from datetime import datetime, timedelta, timezone
import psycopg2
from dotenv import load_dotenv

load_dotenv()  # Pulls your POSTGRES_URL from .env


def seed_test_data():
    conn = psycopg2.connect(os.getenv("POSTGRES_URL"))
    cursor = conn.cursor()

    # We pretend these entries were made 5 days ago, making them due TODAY
    eval_due_today = datetime.now(timezone.utc).date()

    mock_data = [
        # Ticker, Start Price, What the AI guessed, Target Evaluation Date
        ("GDXU", 42.50, 45.00, eval_due_today),
        ("MNTS", 1.15, 0.95, eval_due_today),
    ]

    for ticker, start, pred, target_date in mock_data:
        cursor.execute(
            """
            INSERT INTO predictions (ticker, current_price, predicted_price, target_eval_date)
            VALUES (%s, %s, %s, %s);
        """,
            (ticker, start, pred, target_date),
        )

    conn.commit()
    print(
        f"🎉 Injected mock historical records due for evaluation on {eval_due_today}!"
    )
    cursor.close()
    conn.close()


if __name__ == "__main__":
    seed_test_data()
