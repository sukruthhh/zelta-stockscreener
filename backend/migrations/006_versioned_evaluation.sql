ALTER TABLE predictions ADD COLUMN IF NOT EXISTS actual_close_date DATE;
ALTER TABLE predictions ADD COLUMN IF NOT EXISTS evaluation_version TEXT;
