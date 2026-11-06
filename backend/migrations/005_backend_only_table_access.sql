-- Browser clients use FastAPI; its trusted database connection owns these tables.
-- Prevent direct Supabase Data API access from bypassing backend ownership checks.
DO $$
DECLARE
    managed_table TEXT;
    browser_role TEXT;
BEGIN
    FOREACH managed_table IN ARRAY ARRAY[
        'schema_migrations', 'news_articles', 'portfolios', 'market_scans',
        'predictions', 'watchlists', 'watchlist_items', 'analysis_jobs', 'feedback'
    ] LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', managed_table);
        EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC', managed_table);
        FOREACH browser_role IN ARRAY ARRAY['anon', 'authenticated'] LOOP
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = browser_role) THEN
                EXECUTE format('REVOKE ALL ON TABLE public.%I FROM %I', managed_table, browser_role);
            END IF;
        END LOOP;
    END LOOP;
END $$;
