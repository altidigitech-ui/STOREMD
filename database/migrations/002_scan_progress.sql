ALTER TABLE scans ADD COLUMN IF NOT EXISTS progress integer DEFAULT 0;
ALTER TABLE scans ADD COLUMN IF NOT EXISTS current_step text;
NOTIFY pgrst, 'reload schema';
