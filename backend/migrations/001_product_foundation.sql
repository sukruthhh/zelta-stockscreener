CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS watchlists (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT 'My Watchlist',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, name)
);

CREATE TABLE IF NOT EXISTS watchlist_items (
    id BIGSERIAL PRIMARY KEY,
    watchlist_id BIGINT NOT NULL REFERENCES watchlists(id) ON DELETE CASCADE,
    ticker VARCHAR(10) NOT NULL,
    company_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (watchlist_id, ticker)
);

CREATE TABLE IF NOT EXISTS analysis_jobs (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'gathering_data', 'reading_news', 'calculating_risk', 'complete', 'failed')),
    error_code TEXT,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS analysis_jobs_user_created_idx
    ON analysis_jobs (user_id, created_at DESC);

ALTER TABLE predictions ADD COLUMN IF NOT EXISTS user_id TEXT;
ALTER TABLE predictions ADD COLUMN IF NOT EXISTS analysis_job_id UUID REFERENCES analysis_jobs(id);
ALTER TABLE predictions ADD COLUMN IF NOT EXISTS input_data_timestamp TIMESTAMPTZ;
ALTER TABLE predictions ADD COLUMN IF NOT EXISTS model_version TEXT;
ALTER TABLE predictions ADD COLUMN IF NOT EXISTS result_status TEXT;
ALTER TABLE predictions ADD COLUMN IF NOT EXISTS source_evidence JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE predictions ADD COLUMN IF NOT EXISTS warnings JSONB NOT NULL DEFAULT '[]'::jsonb;

CREATE TABLE IF NOT EXISTS feedback (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    prediction_id INTEGER REFERENCES predictions(id) ON DELETE SET NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
