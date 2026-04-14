-- ============================================================
-- StoreMD — 005_tracking.sql
-- Built-in UTM tracking system: page_views + tracking_events
-- + UTM attribution columns on merchants.
-- ============================================================

CREATE TABLE IF NOT EXISTS page_views (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  session_id text NOT NULL,
  path text NOT NULL,
  referrer text,
  utm_source text,
  utm_medium text,
  utm_campaign text,
  utm_content text,
  utm_term text,
  country text,
  city text,
  device text,
  browser text,
  os text,
  screen_width int,
  ip_hash text,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_page_views_created ON page_views(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_page_views_utm ON page_views(utm_source, utm_medium, utm_campaign);
CREATE INDEX IF NOT EXISTS idx_page_views_session ON page_views(session_id);

CREATE TABLE IF NOT EXISTS tracking_events (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  session_id text NOT NULL,
  event_name text NOT NULL,
  event_data jsonb DEFAULT '{}',
  utm_source text,
  utm_medium text,
  utm_campaign text,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tracking_events_created ON tracking_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tracking_events_name ON tracking_events(event_name);

-- Tables write-only depuis backend (service role).
-- RLS activée mais aucune policy → bloque tout accès anon/authenticated.
ALTER TABLE page_views ENABLE ROW LEVEL SECURITY;
ALTER TABLE tracking_events ENABLE ROW LEVEL SECURITY;

-- UTM attribution sur merchants
ALTER TABLE merchants ADD COLUMN IF NOT EXISTS utm_source text;
ALTER TABLE merchants ADD COLUMN IF NOT EXISTS utm_medium text;
ALTER TABLE merchants ADD COLUMN IF NOT EXISTS utm_campaign text;
ALTER TABLE merchants ADD COLUMN IF NOT EXISTS utm_content text;
ALTER TABLE merchants ADD COLUMN IF NOT EXISTS utm_term text;

NOTIFY pgrst, 'reload schema';
