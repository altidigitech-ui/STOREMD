# QA Agent — Code Review avant commit

> **Sous-agent spécialisé qui review le code avant commit.**
> **Vérifie patterns, types, error handling, sécurité.**
> **Lancé automatiquement via hook pre-commit ou manuellement.**

---

## RÔLE

Le QA Agent vérifie que le code respecte les standards StoreMD AVANT qu'il soit commité. Il ne génère pas de code — il review et bloque si nécessaire.

---

## CE QU'IL VÉRIFIE

### Python (backend)

```
BLOQUANT (le commit est refusé) :
[ ] Pas de `any` équivalent (pas de `# type: ignore` sans raison)
[ ] Pas de `HTTPException` directe → AppError obligatoire
[ ] Pas de `print()` → structlog obligatoire
[ ] Pas de `requests` (sync) → httpx (async) obligatoire
[ ] Pas de `datetime.now()` sans timezone → datetime.now(UTC)
[ ] Pas de `os.getenv()` inline → config.py / settings
[ ] Pas de secrets hardcodés (tokens, clés, mots de passe)
[ ] Pas de `except Exception: pass` (catch-all silencieux)
[ ] Pas de SQL brut avec f-strings
[ ] Pas de `from typing import Optional` → `str | None`

WARNING (commit autorisé mais signalé) :
[ ] Fonctions sans type hints sur le retour
[ ] Fonctions >50 lignes (trop longues, refactor ?)
[ ] Fichiers >300 lignes (trop gros, découper ?)
[ ] TODO/FIXME/HACK dans le code (à tracker)
[ ] Import inutilisé
[ ] Variable non utilisée
```

### TypeScript (frontend)

```
BLOQUANT :
[ ] Pas de `any` → unknown ou type explicite
[ ] Pas de `console.log` en prod (sauf commentaire // debug)
[ ] Pas de `var` → const / let
[ ] Pas de `enum` → as const / union types
[ ] Pas de `dangerouslySetInnerHTML` avec du contenu dynamique
[ ] Pas de fetch() inline → api client centralisé
[ ] Pas de CSS inline ou modules CSS → Tailwind uniquement
[ ] Pas de secrets (NEXT_PUBLIC_ pour les vars publiques uniquement)

WARNING :
[ ] Composants sans data-testid sur les éléments interactifs
[ ] Composants >150 lignes (refactor ?)
[ ] Props non typées
[ ] useEffect sans cleanup
[ ] Missing loading/error states
```

### SQL (migrations)

```
BLOQUANT :
[ ] CREATE TABLE sans ENABLE ROW LEVEL SECURITY
[ ] CREATE TABLE sans policy RLS
[ ] CREATE TABLE avec updated_at mais sans trigger
[ ] Migration sans NOTIFY pgrst
[ ] DROP COLUMN sans confirmation explicite
[ ] SQL avec des données sensibles

WARNING :
[ ] Table sans index sur les colonnes de filtrage fréquent
[ ] Colonne nullable sans DEFAULT explicite
```

### Architecture

```
BLOQUANT :
[ ] Logique métier dans une route API (doit être dans un service)
[ ] Scanner qui appelle Claude API (Claude = node analyze uniquement)
[ ] Scanner qui écrit en DB (retourner ScannerResult, pas write)
[ ] Scanner qui envoie des notifications (node notify uniquement)
[ ] Appel Shopify API depuis le frontend
[ ] Token Shopify en clair (pas chiffré Fernet)
[ ] Endpoint sans check plan pour une feature payante

WARNING :
[ ] Service qui appelle directement la DB sans passer par le Supabase client
[ ] Nouveau fichier sans tests correspondants
```

---

## IMPLÉMENTATION

### Hook pre-commit (settings.json)

Le QA Agent est déclenché via le hook pre-commit dans `.claude/settings.json`. Il lance les vérifications automatiquement avant chaque commit.

### Vérifications automatiques (ruff + eslint)

```bash
# Backend
ruff check app/ tasks/ --select=E,F,W,I,N,UP,S,B
# E = pycodestyle errors
# F = pyflakes
# W = warnings
# I = isort
# N = pep8-naming
# UP = pyupgrade (Python 3.12+ patterns)
# S = bandit (security)
# B = bugbear (common bugs)

# Frontend
npx eslint src/ --ext .ts,.tsx --max-warnings=0
npx tsc --noEmit
```

### Vérifications manuelles (le QA agent lit le code)

Pour les règles qui ne sont pas dans ruff/eslint (architecture, patterns StoreMD), le QA agent lit les fichiers modifiés et vérifie manuellement.

```
Processus :
1. Identifier les fichiers modifiés (git diff --staged --name-only)
2. Pour chaque fichier .py → vérifier les patterns Python
3. Pour chaque fichier .ts/.tsx → vérifier les patterns TypeScript
4. Pour chaque fichier .sql → vérifier les patterns SQL
5. Pour chaque nouveau scanner → vérifier BaseScanner + registry + test
6. Rapport : BLOQUANT (refuse) ou WARNING (signale)
```

---

## OUTPUT

```
=== QA AGENT REVIEW ===

Files reviewed: 5

BLOQUANT:
  ❌ backend/app/api/routes/scans.py:42
     HTTPException used directly. Use AppError with ErrorCode.
  ❌ frontend/src/components/dashboard/Score.tsx:18
     Type 'any' found. Use explicit type or 'unknown'.

WARNING:
  ⚠️ backend/app/services/scan_service.py:89
     Function 'process_results' is 67 lines. Consider refactoring.
  ⚠️ frontend/src/components/scan/ScanProgress.tsx
     Missing data-testid on progress bar element.

PASSED:
  ✅ backend/app/agent/analyzers/email_health.py — OK
  ✅ backend/tests/test_analyzers/test_email_health.py — OK
  ✅ database/migrations/004_add_email_health.sql — OK

RESULT: ❌ BLOCKED — fix 2 issues before committing
```
