from pathlib import Path

import psycopg2

from config import get_settings


MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def run_migrations() -> None:
    with psycopg2.connect(get_settings().postgres_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations "
                "(version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW())"
            )
            for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
                cursor.execute("SELECT 1 FROM schema_migrations WHERE version = %s", (path.name,))
                if cursor.fetchone():
                    continue
                cursor.execute(path.read_text(encoding="utf-8"))
                cursor.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (path.name,))

