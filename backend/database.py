import psycopg2
import os
from dotenv import load_dotenv
from psycopg2.extras import execute_values
from datetime import datetime, timedelta

load_dotenv()


def init_db():
    """
    Creates all required tables if they don't already exist.
    Runs automatically on server startup.
    """
    db = psycopg2.connect(os.getenv("POSTGRES_URL"))
    cursor = db.cursor()
    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS news_articles (
            id SERIAL PRIMARY KEY,
            ticker TEXT NOT NULL,
            headline TEXT NOT NULL,
            summary TEXT,
            url TEXT,
            published_at TIMESTAMP,
            content_chunk TEXT NOT NULL,
            embedding vector(1536),
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS news_embedding_idx 
        ON news_articles USING ivfflat (embedding vector_cosine_ops);
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolios (
            id SERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            ticker TEXT NOT NULL,
            shares NUMERIC NOT NULL,
            avg_cost NUMERIC NOT NULL,
            added_at TIMESTAMP DEFAULT NOW()
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_scans (
            id SERIAL PRIMARY KEY,
            ticker VARCHAR(10) NOT NULL,
            scan_date DATE NOT NULL,
            close_price NUMERIC(10, 4),
            annualized_volatility NUMERIC(6, 4),
            volume_spike_ratio NUMERIC(6, 4),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(ticker, scan_date)
        );
    """)

    cursor.execute("""
        ALTER TABLE market_scans
        ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id SERIAL PRIMARY KEY,
            ticker TEXT NOT NULL,
            current_price NUMERIC(10,4),
            predicted_price NUMERIC(10,4),       -- The AI's price target forecast
            volume_spike_ratio NUMERIC(6,4),
            atr_14 NUMERIC(10,4),
            final_bias TEXT,
            confidence_score NUMERIC(4,3),
            calculated_stop_loss NUMERIC(10,4),
            risk_rationale TEXT,
            raw_agent_output TEXT,

            -- Backtesting Metrics
            target_eval_date DATE,                 -- Created_at + 5 Days
            actual_close_price NUMERIC(10,4),      -- Real price from yfinance
            absolute_error_pct NUMERIC(6,2),       -- MAPE margin
            is_correct_direction BOOLEAN,           -- Directional hit/miss flag
            is_evaluated BOOLEAN DEFAULT FALSE,     -- Operational state tracking

            backtest_status TEXT DEFAULT 'pending',
            actual_outcome TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)

    db.commit()
    cursor.close()
    db.close()
    print("Database tables initialised successfully.")


def save_scan_results(alerts: dict):
    """
    Saves morning scanner results to the market_scans table.
    Updates existing records if the same ticker was already scanned today.
    """
    if not alerts:
        return

    query = """
        INSERT INTO market_scans (ticker, scan_date, close_price, annualized_volatility, volume_spike_ratio)
        VALUES %s
        ON CONFLICT (ticker, scan_date)
        DO UPDATE SET
            close_price = EXCLUDED.close_price,
            annualized_volatility = EXCLUDED.annualized_volatility,
            volume_spike_ratio = EXCLUDED.volume_spike_ratio,
            updated_at = CURRENT_TIMESTAMP;
    """

    today = datetime.now().date()
    records = []
    for ticker, data in alerts.items():
        summary = data.get("latest_summary", {})
        records.append(
            (
                ticker.upper(),
                today,
                summary.get("current_close"),
                summary.get("annualized_volatility"),
                summary.get("volume_spike_ratio"),
            )
        )

    db = psycopg2.connect(os.getenv("POSTGRES_URL"))
    try:
        cursor = db.cursor()
        execute_values(cursor, query, records)
        db.commit()
        cursor.close()
        print(f"Saved {len(records)} scan results to database.")
    except Exception as e:
        db.rollback()
        print(f"Error saving scan results: {e}")
    finally:
        db.close()


def get_database_verification_snapshot(limit: int = 10, ticker: str | None = None):
    """Return a compact snapshot of recently stored rows for Swagger-based verification."""
    db = psycopg2.connect(os.getenv("POSTGRES_URL"))
    cursor = db.cursor()

    try:
        ticker_filter = ticker.upper() if ticker else None

        if ticker_filter:
            cursor.execute(
                "SELECT COUNT(*) FROM market_scans WHERE ticker = %s;", (ticker_filter,)
            )
        else:
            cursor.execute("SELECT COUNT(*) FROM market_scans;")
        market_scan_count = cursor.fetchone()[0]

        if ticker_filter:
            cursor.execute(
                "SELECT COUNT(*) FROM news_articles WHERE ticker = %s;",
                (ticker_filter,),
            )
        else:
            cursor.execute("SELECT COUNT(*) FROM news_articles;")
        news_article_count = cursor.fetchone()[0]

        if ticker_filter:
            cursor.execute(
                """
                SELECT ticker, scan_date, close_price, annualized_volatility, volume_spike_ratio, created_at, updated_at
                FROM market_scans
                WHERE ticker = %s
                ORDER BY updated_at DESC, id DESC
                LIMIT %s;
                """,
                (ticker_filter, limit),
            )
        else:
            cursor.execute(
                """
                SELECT ticker, scan_date, close_price, annualized_volatility, volume_spike_ratio, created_at, updated_at
                FROM market_scans
                ORDER BY updated_at DESC, id DESC
                LIMIT %s;
                """,
                (limit,),
            )
        recent_market_scans = [
            {
                "ticker": row[0],
                "scan_date": row[1].isoformat() if row[1] else None,
                "close_price": float(row[2]) if row[2] is not None else None,
                "annualized_volatility": float(row[3]) if row[3] is not None else None,
                "volume_spike_ratio": float(row[4]) if row[4] is not None else None,
                "created_at": row[5].isoformat() if row[5] else None,
                "updated_at": row[6].isoformat() if row[6] else None,
            }
            for row in cursor.fetchall()
        ]

        if ticker_filter:
            cursor.execute(
                """
                SELECT ticker, headline, created_at
                FROM news_articles
                WHERE ticker = %s
                ORDER BY created_at DESC, id DESC
                LIMIT %s;
                """,
                (ticker_filter, limit),
            )
        else:
            cursor.execute(
                """
                SELECT ticker, headline, created_at
                FROM news_articles
                ORDER BY created_at DESC, id DESC
                LIMIT %s;
                """,
                (limit,),
            )
        recent_news_articles = [
            {
                "ticker": row[0],
                "headline": row[1],
                "created_at": row[2].isoformat() if row[2] else None,
            }
            for row in cursor.fetchall()
        ]

        return {
            "ticker_filter": ticker_filter,
            "market_scans": {
                "count": market_scan_count,
                "recent_rows": recent_market_scans,
            },
            "news_articles": {
                "count": news_article_count,
                "recent_rows": recent_news_articles,
            },
        }
    finally:
        cursor.close()
        db.close()


def save_prediction(ticker: str, market_data: dict, agent_result: dict):
    db = psycopg2.connect(os.getenv("POSTGRES_URL"))
    cursor = db.cursor()

    # Pre-calculate evaluation target (5 calendar days out)
    target_date = (datetime.utcnow() + timedelta(days=5)).date()

    cursor.execute(
        """
        INSERT INTO predictions 
        (
            ticker, current_price, predicted_price, volume_spike_ratio, atr_14, 
            final_bias, confidence_score, calculated_stop_loss, risk_rationale,
            raw_agent_output, target_eval_date
        ) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """,
        (
            ticker,
            float(market_data.get("current_price") or 0),
            (
                float(agent_result["predicted_price"])
                if agent_result.get("predicted_price") is not None
                else None
            ),
            float(market_data.get("volume_spike_ratio") or 0),
            float(market_data.get("atr_14") or 0),
            agent_result.get("final_bias"),
            (
                float(agent_result["confidence_score"])
                if agent_result.get("confidence_score") is not None
                else None
            ),
            (
                float(agent_result["calculated_stop_loss"])
                if agent_result.get("calculated_stop_loss") is not None
                else None
            ),
            agent_result.get("risk_rationale"),
            agent_result.get("ai_analysis"),
            target_date,
        ),
    )

    generated_id = cursor.fetchone()[0]
    db.commit()
    cursor.close()
    db.close()

    return generated_id
