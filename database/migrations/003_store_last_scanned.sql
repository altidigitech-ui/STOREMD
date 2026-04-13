ALTER TABLE stores ADD COLUMN IF NOT EXISTS last_scanned_at timestamptz;
NOTIFY pgrst, 'reload schema';
