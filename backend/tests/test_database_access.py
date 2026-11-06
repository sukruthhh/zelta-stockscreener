from uuid import uuid4

import psycopg2
from psycopg2 import sql
import pytest

from config import get_settings
from migrations import MIGRATIONS_DIR


def test_browser_role_cannot_bypass_backend_ownership_checks(require_postgres):
    role = f"browser_test_{uuid4().hex}"
    connection = psycopg2.connect(get_settings().postgres_url)
    try:
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO watchlists (user_id, name) VALUES (%s, 'Private') RETURNING id", (f"owner-{uuid4()}",))
            row_id = cursor.fetchone()[0]
            cursor.execute(sql.SQL("CREATE ROLE {} NOLOGIN").format(sql.Identifier(role)))
            cursor.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(role)))
            cursor.execute(sql.SQL("GRANT SELECT, INSERT ON public.watchlists TO {}").format(sql.Identifier(role)))
            cursor.execute(sql.SQL("GRANT USAGE ON SEQUENCE public.watchlists_id_seq TO {}").format(sql.Identifier(role)))
            cursor.execute(sql.SQL("SET LOCAL ROLE {}").format(sql.Identifier(role)))
            cursor.execute("SELECT id FROM watchlists WHERE id = %s", (row_id,))
            assert cursor.fetchall() == []
            with pytest.raises(psycopg2.errors.InsufficientPrivilege, match="row-level security"):
                cursor.execute("INSERT INTO watchlists (user_id, name) VALUES ('other-user', 'Bypass')")
    finally:
        # Roll back the test role, grants and row, including after the expected denied write.
        connection.rollback()
        connection.close()


def test_every_managed_table_enables_row_security(require_postgres):
    tables = {"schema_migrations", "news_articles", "portfolios", "market_scans", "predictions", "watchlists", "watchlist_items", "analysis_jobs", "feedback"}
    with psycopg2.connect(get_settings().postgres_url) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT relname, relrowsecurity FROM pg_class JOIN pg_namespace ON pg_namespace.oid = relnamespace WHERE nspname = 'public' AND relname = ANY(%s)", (list(tables),))
        results = dict(cursor.fetchall())
    assert set(results) == tables
    assert all(results.values())


def test_migration_revokes_supabase_browser_roles_even_if_previously_granted(require_postgres):
    connection = psycopg2.connect(get_settings().postgres_url)
    try:
        with connection.cursor() as cursor:
            for role in ("anon", "authenticated"):
                cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
                if not cursor.fetchone():
                    cursor.execute(sql.SQL("CREATE ROLE {} NOLOGIN").format(sql.Identifier(role)))
                cursor.execute(sql.SQL("GRANT SELECT ON public.watchlists TO {}").format(sql.Identifier(role)))
            cursor.execute((MIGRATIONS_DIR / "005_backend_only_table_access.sql").read_text(encoding="utf-8"))
            for role in ("anon", "authenticated"):
                cursor.execute("SELECT has_table_privilege(%s, 'public.watchlists', 'SELECT')", (role,))
                assert cursor.fetchone()[0] is False
    finally:
        connection.rollback()
        connection.close()
