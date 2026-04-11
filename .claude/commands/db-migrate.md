# /db-migrate — Appliquer une migration SQL

> **Commande slash pour appliquer une migration Supabase en toute sécurité.**
> **Vérifie, exécute, NOTIFY pgrst, vérifie le RLS.**
> **Usage : `/db-migrate` ou `/db-migrate 003_add_column`**

---

## USAGE

```
/db-migrate                    → Applique la prochaine migration non appliquée
/db-migrate 003_add_column     → Applique une migration spécifique
/db-migrate check              → Liste les migrations et leur status
/db-migrate rollback 003       → Applique le rollback d'une migration
```

---

## PROCÉDURE

### Étape 1 — Identifier la migration

```bash
# Lister les migrations disponibles
ls -la database/migrations/

# Output attendu :
# 001_initial.sql            ← déjà appliquée
# 002_add_notification_cat.sql  ← à appliquer
# 003_add_views_column.sql      ← future
```

### Étape 2 — Vérifier le contenu

```bash
# Lire la migration avant de l'appliquer
cat database/migrations/002_add_notification_cat.sql
```

Vérifier :
```
[ ] Le SQL est syntaxiquement correct
[ ] Si CREATE TABLE → RLS policy incluse
[ ] Si CREATE TABLE → Trigger updated_at inclus
[ ] Si ALTER TABLE → Pas de perte de données (DROP COLUMN = données perdues)
[ ] Indexes pertinents ajoutés
[ ] NOTIFY pgrst à la fin
[ ] Pas de données sensibles dans le SQL (pas de tokens, pas d'emails)
```

### Étape 3 — Appliquer la migration

**Option A — Via Supabase SQL Editor (dashboard)**

```
1. Ouvrir https://supabase.com/dashboard → projet StoreMD → SQL Editor
2. Coller le contenu de database/migrations/XXX.sql
3. Cliquer "Run"
4. Vérifier le résultat (pas d'erreur)
5. Exécuter : NOTIFY pgrst, 'reload schema';
```

**Option B — Via MCP Supabase dans Claude Code**

```
Prompt : "Exécute le SQL suivant via MCP Supabase : [coller le SQL]"
Puis : "Exécute NOTIFY pgrst, 'reload schema';"
```

**Option C — Via psql (CLI)**

```bash
psql $SUPABASE_DB_URL -f database/migrations/002_add_notification_cat.sql
psql $SUPABASE_DB_URL -c "NOTIFY pgrst, 'reload schema';"
```

### Étape 4 — Vérifier le résultat

```sql
-- Vérifier que la migration a été appliquée

-- Si nouvelle table :
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name = 'new_table';

-- Si nouvelle colonne :
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'existing_table' AND column_name = 'new_column';

-- Si nouvel index :
SELECT indexname FROM pg_indexes
WHERE tablename = 'table_name' AND indexname = 'idx_new_index';

-- Vérifier le RLS (si nouvelle table)
SELECT tablename, rowsecurity FROM pg_tables
WHERE schemaname = 'public' AND tablename = 'new_table';
-- rowsecurity doit être true

-- Vérifier les policies RLS
SELECT policyname, cmd, qual FROM pg_policies
WHERE tablename = 'new_table';
```

### Étape 5 — Tester le RLS (si applicable)

```sql
-- Simuler un merchant authentifié
SET request.jwt.claims = '{"sub": "test-merchant-uuid", "role": "authenticated"}';
SET role = 'authenticated';

-- Tester que le RLS fonctionne
SELECT * FROM new_table;  -- Doit retourner 0 rows (pas de données pour ce merchant)

-- Insérer une row de test
INSERT INTO new_table (merchant_id, store_id, ...)
VALUES ('test-merchant-uuid', 'test-store-uuid', ...);

-- Vérifier qu'on la voit
SELECT * FROM new_table;  -- Doit retourner 1 row

-- Simuler un AUTRE merchant
SET request.jwt.claims = '{"sub": "other-merchant-uuid", "role": "authenticated"}';
SELECT * FROM new_table;  -- Doit retourner 0 rows (RLS bloque)

-- Reset
RESET role;
RESET request.jwt.claims;

-- Cleanup
DELETE FROM new_table WHERE merchant_id = 'test-merchant-uuid';
```

### Étape 6 — Mettre à jour la documentation

```
[ ] docs/DATABASE.md mis à jour avec la nouvelle table/colonne
[ ] docs/CHANGELOG.md mis à jour (section Infrastructure)
```

---

## CRÉER UNE NOUVELLE MIGRATION

### Template

```sql
-- database/migrations/XXX_description.sql
-- Date: YYYY-MM-DD
-- Description: What this migration does
-- Author: [who]

-- ============================================================
-- CHANGES
-- ============================================================

-- [SQL ici]

-- ============================================================
-- RLS (si nouvelle table)
-- ============================================================

-- ALTER TABLE new_table ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "merchants_own_new_table" ON new_table
--     FOR ALL USING (merchant_id = auth.uid());

-- ============================================================
-- TRIGGER updated_at (si nouvelle table mutable)
-- ============================================================

-- CREATE TRIGGER new_table_updated_at BEFORE UPDATE ON new_table
--     FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- POST-MIGRATION
-- ============================================================

NOTIFY pgrst, 'reload schema';
```

### Convention de nommage

```
Format : {numero_3_digits}_{description_snake_case}.sql

Exemples :
  001_initial.sql
  002_add_notification_category.sql
  003_add_product_views_column.sql
  004_create_audit_log_table.sql
  005_add_index_scans_score.sql
  006_rollback_004.sql
```

Numérotation séquentielle, jamais de gaps.

---

## ROLLBACK

```sql
-- database/migrations/XXX_rollback_YYY.sql
-- Rollback de la migration YYY
-- Date: YYYY-MM-DD

-- Si ALTER TABLE ADD COLUMN :
ALTER TABLE table_name DROP COLUMN column_name;

-- Si CREATE TABLE :
DROP TABLE IF EXISTS table_name;

-- Si CREATE INDEX :
DROP INDEX IF EXISTS idx_name;

NOTIFY pgrst, 'reload schema';
```

**Attention :** DROP COLUMN et DROP TABLE sont des opérations DESTRUCTIVES. Vérifier 3 fois avant de rollback en production. Faire un backup Supabase avant si nécessaire.

---

## RÈGLES

- ❌ Modifier le schéma sans migration numérotée → ✅ Toujours un fichier dans `database/migrations/`
- ❌ Migration sans `NOTIFY pgrst` → ✅ Toujours terminer par `NOTIFY pgrst, 'reload schema'`
- ❌ CREATE TABLE sans RLS → ✅ RLS + policy dans le même fichier
- ❌ CREATE TABLE sans trigger `updated_at` → ✅ Si la table a `updated_at`, ajouter le trigger
- ❌ Appliquer la migration APRÈS le deploy code → ✅ Toujours AVANT
- ❌ DROP COLUMN en prod sans backup → ✅ Backup Supabase avant toute suppression
- ❌ Migration qui casse le schéma existant (rename column) → ✅ Add new + migrate data + drop old (3 steps)
- ❌ Oublier de mettre à jour DATABASE.md → ✅ Toujours sync après migration
