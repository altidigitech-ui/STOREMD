-- ============================================================
-- StoreMD — 007_preview_leads.sql
-- Email capture from preview scan results page.
-- NE PAS EXÉCUTER AUTOMATIQUEMENT — appliquer dans Supabase SQL Editor.
-- ============================================================

CREATE TABLE IF NOT EXISTS preview_leads (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  email text NOT NULL,
  shop_domain text NOT NULL,
  score int,
  issues_total int NOT NULL DEFAULT 0,
  ip_hash text,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_preview_leads_created ON preview_leads(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_preview_leads_email ON preview_leads(email);
CREATE UNIQUE INDEX IF NOT EXISTS idx_preview_leads_email_domain ON preview_leads(email, shop_domain);

ALTER TABLE preview_leads ENABLE ROW LEVEL SECURITY;

NOTIFY pgrst, 'reload schema';
