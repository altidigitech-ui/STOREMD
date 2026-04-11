# Skill: Supabase Patterns

> **Utilise ce skill quand tu travailles avec Supabase :**
> **Queries, RLS, migrations, auth, storage, realtime, service role vs anon.**

---

## QUAND UTILISER

- Écrire des queries Supabase (CRUD)
- Créer/modifier des tables et migrations
- Configurer les RLS policies
- Utiliser Supabase Auth (JWT, sessions)
- Uploader/télécharger des fichiers (Storage)
- Débugger des erreurs DB ou RLS

---

## CLIENT SETUP

### Backend (service_role — accès complet, bypass RLS)

```python
# app/services/supabase.py

from supabase import create_client, Client
from app.config import settings

def get_supabase_service() -> Client:
    """Client service_role — BACKEND ONLY.
    
    Bypass RLS. Utilisé pour :
    - Webhooks (traitement cross-merchant)
    - Tâches admin (cleanup, migrations runtime)
    - Cross-store intelligence
    
    JAMAIS exposé au frontend. JAMAIS dans les logs.
    """
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_ROLE_KEY,
    )


def get_supabase_anon() -> Client:
    """Client anon — respecte le RLS.
    
    Utilisé dans les routes API avec le JWT du merchant.
    Le RLS filtre automatiquement par merchant_id.
    """
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_ANON_KEY,
    )
```

### Frontend (anon key — RLS actif)

```typescript
// lib/supabase.ts

import { createBrowserClient } from "@supabase/ssr";

export const supabase = createBrowserClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
);
```

### Quand utiliser quel client ?

| Contexte | Client | RLS |
|----------|--------|-----|
| Route API avec JWT merchant | anon + JWT header | ✅ Actif — merchant voit ses données |
| Webhook handler (pas de JWT) | service_role | ❌ Bypass — accès cross-merchant |
| Celery task (background) | service_role | ❌ Bypass — pas de session user |
| Frontend (browser) | anon + session | ✅ Actif |
| Migration runtime | service_role | ❌ Bypass |

---

## QUERY PATTERNS

### Select (single row)

```python
# Avec .single() — raise si 0 ou >1 résultat
result = await supabase.table("merchants").select("*").eq(
    "id", merchant_id
).single().execute()
merchant = result.data  # dict

# Avec .maybe_single() — retourne None si 0 résultat (pas de raise)
result = await supabase.table("stores").select("*").eq(
    "shopify_shop_domain", domain
).maybe_single().execute()
store = result.data  # dict | None
```

**Règle : utiliser `.maybe_single()` quand l'absence de résultat est un cas valide (lookup par domain, check existence). Utiliser `.single()` quand l'absence est une erreur (get by ID après vérification d'existence).**

### Select (multiple rows, paginated)

```python
# Pagination cursor-based
result = await supabase.table("scans").select("*").eq(
    "store_id", store_id
).order("created_at", desc=True).range(
    offset, offset + page_size - 1
).execute()
scans = result.data  # list[dict]
```

### Select (avec colonnes spécifiques)

```python
# Ne charger que ce dont on a besoin
result = await supabase.table("scan_issues").select(
    "id, severity, title, fix_applied"
).eq("scan_id", scan_id).execute()
```

### Insert

```python
result = await supabase.table("scans").insert({
    "store_id": store_id,
    "merchant_id": merchant_id,
    "status": "pending",
    "trigger": "manual",
    "modules": modules,
}).execute()
scan = result.data[0]  # dict avec l'ID généré
```

### Insert multiple

```python
issues = [
    {
        "scan_id": scan_id,
        "store_id": store_id,
        "merchant_id": merchant_id,
        "module": issue.module,
        "scanner": issue.scanner,
        "severity": issue.severity,
        "title": issue.title,
        "description": issue.description,
        "impact": issue.impact,
        "fix_type": issue.fix_type,
        "fix_description": issue.fix_description,
        "auto_fixable": issue.auto_fixable,
        "context": issue.context,
    }
    for issue in scan_issues
]
result = await supabase.table("scan_issues").insert(issues).execute()
```

### Update

```python
result = await supabase.table("scans").update({
    "status": "completed",
    "score": score,
    "mobile_score": mobile_score,
    "desktop_score": desktop_score,
    "issues_count": issues_count,
    "completed_at": datetime.now(UTC).isoformat(),
}).eq("id", scan_id).execute()
# updated_at est géré automatiquement par le trigger
```

### Upsert

```python
# Insert ou update si existe (basé sur UNIQUE constraint)
result = await supabase.table("store_apps").upsert({
    "store_id": store_id,
    "merchant_id": merchant_id,
    "shopify_app_id": app_id,
    "name": app_name,
    "impact_ms": impact_ms,
    "last_seen_at": datetime.now(UTC).isoformat(),
}, on_conflict="store_id,shopify_app_id").execute()
```

### Delete

```python
# Soft delete (preferred pour les stores)
await supabase.table("stores").update({
    "status": "uninstalled",
    "uninstalled_at": datetime.now(UTC).isoformat(),
}).eq("id", store_id).execute()

# Hard delete (pour les données temporaires)
await supabase.table("webhook_events").delete().eq(
    "id", event_id
).execute()
```

### Filtres avancés

```python
# IN
result = await supabase.table("scans").select("*").in_(
    "status", ["pending", "running"]
).execute()

# Comparaison
result = await supabase.table("scan_issues").select("*").eq(
    "scan_id", scan_id
).gte("impact_value", 1.0).order("impact_value", desc=True).execute()

# NOT
result = await supabase.table("store_apps").select("*").eq(
    "store_id", store_id
).neq("status", "uninstalled").execute()

# IS NULL / IS NOT NULL
result = await supabase.table("product_analyses").select("*").is_(
    "hs_code", "null"
).execute()

# LIKE / ILIKE
result = await supabase.table("scan_issues").select("*").ilike(
    "title", "%Privy%"
).execute()
```

---

## RLS — ROW LEVEL SECURITY

### Pattern standard

```sql
-- TOUJOURS activer RLS
ALTER TABLE my_table ENABLE ROW LEVEL SECURITY;

-- Policy standard : merchant voit ses données
CREATE POLICY "merchants_own_my_table" ON my_table
    FOR ALL USING (merchant_id = auth.uid());
```

### Policies séparées par opération

```sql
-- Quand on veut des permissions fines
CREATE POLICY "merchants_read_own" ON merchants
    FOR SELECT USING (id = auth.uid());

CREATE POLICY "merchants_update_own" ON merchants
    FOR UPDATE USING (id = auth.uid());

-- INSERT/DELETE via service_role uniquement
```

### Policy service_role only

```sql
-- Pour les tables que le frontend ne doit JAMAIS toucher
CREATE POLICY "service_role_only" ON webhook_events
    FOR ALL USING (auth.role() = 'service_role');
```

### Tester le RLS

```sql
-- Dans Supabase SQL Editor
-- Simuler un merchant authentifié
SET request.jwt.claims = '{"sub": "merchant-uuid-1", "role": "authenticated"}';
SET role = 'authenticated';

-- Cette query doit retourner UNIQUEMENT les scans du merchant-uuid-1
SELECT * FROM scans;

-- Cette query doit retourner 0 rows (RLS bloque)
SELECT * FROM scans WHERE merchant_id = 'merchant-uuid-2';

-- Reset
RESET role;
RESET request.jwt.claims;
```

### Pièges RLS courants

| Piège | Symptôme | Fix |
|-------|----------|-----|
| Oublier `ENABLE ROW LEVEL SECURITY` | Toutes les données sont visibles | Toujours vérifier après `CREATE TABLE` |
| Policy manquante pour INSERT | Insert échoue avec permission denied | Ajouter `FOR ALL` ou `FOR INSERT` policy |
| service_role utilisé côté frontend | RLS bypassé, faille de sécurité | JAMAIS exposer service_role au frontend |
| merchant_id non rempli à l'insert | RLS retourne 0 rows au SELECT | Toujours inclure merchant_id dans chaque INSERT |
| `auth.uid()` retourne NULL | Aucune donnée visible | Vérifier que le JWT est transmis au client Supabase |

---

## MIGRATIONS

### Convention

```
database/migrations/
├── 001_initial.sql              # Schéma complet (depuis DATABASE.md)
├── 002_add_notification_category.sql
├── 003_add_product_views_column.sql
└── ...
```

### Template migration

```sql
-- database/migrations/XXX_description.sql
-- Date: YYYY-MM-DD
-- Description: What this migration does

-- === CHANGES ===

ALTER TABLE products_analyses ADD COLUMN views_30d INTEGER DEFAULT 0;

CREATE INDEX idx_products_views ON product_analyses(views_30d DESC);

-- === POST-MIGRATION ===

NOTIFY pgrst, 'reload schema';
```

### Exécution

Via Supabase SQL Editor (dashboard) ou via MCP Supabase dans Claude Code :
```
Exécute le SQL de migration complet via MCP Supabase
```

**TOUJOURS** terminer par `NOTIFY pgrst, 'reload schema';` pour que PostgREST recharge le schéma. Sans ça, les nouvelles colonnes/tables ne sont pas accessibles via le client Supabase.

### Rollback

Pas de rollback automatique. Écrire la migration inverse manuellement si nécessaire :

```sql
-- database/migrations/XXX_rollback_description.sql
ALTER TABLE product_analyses DROP COLUMN views_30d;
NOTIFY pgrst, 'reload schema';
```

---

## SUPABASE AUTH

### Trigger auto-creation merchant

```sql
-- Déjà dans DATABASE.md — crée un profil merchant à chaque inscription
CREATE OR REPLACE FUNCTION on_auth_user_created()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO merchants (id, email)
    VALUES (NEW.id, NEW.email);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER create_merchant_on_signup
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION on_auth_user_created();
```

### Valider le JWT dans FastAPI

```python
# Le middleware auth.py (voir SECURITY.md) utilise :
user_response = supabase.auth.get_user(token)
# Supabase vérifie signature + expiration
# Retourne le user avec son ID (= merchant_id)
```

### Session management

Le frontend utilise `@supabase/ssr` pour gérer les sessions :
- Token stocké dans les cookies (httpOnly, secure)
- Refresh automatique par le client Supabase
- Le backend valide le JWT à chaque requête

---

## SUPABASE STORAGE

### Buckets

| Bucket | Contenu | Accès |
|--------|---------|-------|
| `screenshots` | Visual Store Test screenshots | Private — path-based policy |
| `reports` | Weekly reports PDF | Private |
| `backups` | Collection backups JSON | Private |

### Upload (backend)

```python
# Depuis le worker Celery (service_role)
supabase = get_supabase_service()
supabase.storage.from_("screenshots").upload(
    path=f"{store_id}/{scan_id}/mobile.png",
    file=screenshot_bytes,
    file_options={"content-type": "image/png"},
)
```

### Download (backend)

```python
file_bytes = supabase.storage.from_("screenshots").download(
    f"{store_id}/{scan_id}/mobile.png"
)
```

### Public URL (pour le frontend)

```python
url = supabase.storage.from_("screenshots").get_public_url(
    f"{store_id}/{scan_id}/mobile.png"
)
# Retourne une URL signée si le bucket est private
```

### Storage policy

```sql
-- Chaque merchant accède uniquement à ses fichiers
-- Le path commence par le store_id, qui est lié au merchant_id
CREATE POLICY "merchant_storage_access" ON storage.objects
    FOR ALL USING (
        bucket_id IN ('screenshots', 'reports', 'backups')
        AND (storage.foldername(name))[1] IN (
            SELECT id::text FROM stores WHERE merchant_id = auth.uid()
        )
    );
```

---

## ERREURS COURANTES

| Erreur | Cause | Fix |
|--------|-------|-----|
| `PGRST301: JWSError` | JWT invalide ou expiré | Vérifier le token, refresh la session |
| `new row violates RLS policy` | Insert sans merchant_id ou mauvais merchant_id | Toujours inclure merchant_id |
| `relation does not exist` | Table pas dans le schéma PostgREST | `NOTIFY pgrst, 'reload schema'` |
| `duplicate key value violates unique constraint` | Insert en double (idempotency) | Utiliser upsert ou check before insert |
| `permission denied for table` | RLS actif mais pas de policy pour cette opération | Ajouter la policy manquante |
| `Could not find the function` | RPC function pas créée ou pas dans le schéma | `NOTIFY pgrst, 'reload schema'` |
| `column does not exist` | Migration non appliquée ou schema pas rechargé | Appliquer la migration + NOTIFY |

---

## INTERDICTIONS

- ❌ `service_role` dans le frontend → ✅ Uniquement `anon` key côté client
- ❌ `service_role` dans les logs → ✅ Jamais logger les clés
- ❌ Table sans RLS → ✅ `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` sur CHAQUE table
- ❌ Insert sans `merchant_id` → ✅ Toujours inclure pour que le RLS fonctionne
- ❌ Migration sans `NOTIFY pgrst` → ✅ Toujours terminer par `NOTIFY pgrst, 'reload schema'`
- ❌ `.single()` quand l'absence est valide → ✅ `.maybe_single()` pour les lookups optionnels
- ❌ `SELECT *` sur les grosses tables → ✅ Sélectionner les colonnes nécessaires
- ❌ Queries sans pagination → ✅ `.range()` ou cursor-based sur les listes
