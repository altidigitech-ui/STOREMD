# /full-test — Lancer tous les tests StoreMD

> **Commande slash pour exécuter la suite de tests complète.**
> **Usage : `/full-test` ou `/full-test backend` ou `/full-test frontend`**

---

## USAGE

```
/full-test              → Tous les tests (backend + frontend + lint)
/full-test backend      → pytest uniquement
/full-test frontend     → vitest uniquement
/full-test lint         → Lint uniquement (ruff + eslint)
/full-test quick        → Unit tests seulement (pas d'intégration, rapide)
/full-test e2e          → Tests Playwright E2E
```

---

## PROCÉDURE COMPLÈTE

### 1. Lint

```bash
echo "=== LINT BACKEND ==="
cd backend
ruff check app/ tasks/ tests/
ruff format --check app/ tasks/ tests/
echo "✅ Backend lint OK"

echo ""
echo "=== LINT FRONTEND ==="
cd frontend
npm run lint
echo "✅ Frontend lint OK"
```

### 2. Tests backend

```bash
echo ""
echo "=== TESTS BACKEND — UNIT ==="
cd backend
pytest -m unit -x --tb=short -q
echo "✅ Unit tests OK"

echo ""
echo "=== TESTS BACKEND — INTEGRATION ==="
pytest -m integration -x --tb=short -q
echo "✅ Integration tests OK"

echo ""
echo "=== COVERAGE BACKEND ==="
pytest --cov=app --cov-report=term-missing --cov-fail-under=70
echo "✅ Coverage OK (>70%)"
```

### 3. Tests frontend

```bash
echo ""
echo "=== TESTS FRONTEND ==="
cd frontend
npm test -- --run --reporter=verbose
echo "✅ Frontend tests OK"

echo ""
echo "=== COVERAGE FRONTEND ==="
npm test -- --run --coverage
echo "✅ Frontend coverage OK"
```

### 4. Type check frontend

```bash
echo ""
echo "=== TYPE CHECK ==="
cd frontend
npx tsc --noEmit
echo "✅ TypeScript types OK"
```

### 5. Build check

```bash
echo ""
echo "=== BUILD CHECK FRONTEND ==="
cd frontend
npm run build
echo "✅ Frontend build OK"

echo ""
echo "=== BUILD CHECK BACKEND (Docker) ==="
cd backend
docker build -t storemd-api-test . --quiet
echo "✅ Backend Docker build OK"
```

### 6. Sécurité (optionnel, pas bloquant)

```bash
echo ""
echo "=== SECURITY CHECKS ==="

# Secrets dans le code
cd ..
SECRETS_FOUND=$(grep -rn "sk_live\|sk_test_\|whsec_\|sk-ant-\|eyJhbG" backend/app/ frontend/src/ --include="*.py" --include="*.ts" --include="*.tsx" 2>/dev/null | wc -l)
if [ "$SECRETS_FOUND" -gt 0 ]; then
    echo "❌ SECRETS FOUND IN CODE!"
    grep -rn "sk_live\|sk_test_\|whsec_\|sk-ant-" backend/app/ frontend/src/ --include="*.py" --include="*.ts" --include="*.tsx"
    exit 1
fi
echo "✅ No secrets in code"

# print() dans le backend
PRINTS_FOUND=$(grep -rn "print(" backend/app/ --include="*.py" | grep -v "# noqa" | wc -l)
if [ "$PRINTS_FOUND" -gt 0 ]; then
    echo "⚠️  print() found in backend (use structlog):"
    grep -rn "print(" backend/app/ --include="*.py" | grep -v "# noqa"
fi

# any dans le frontend
ANY_FOUND=$(grep -rn ": any" frontend/src/ --include="*.ts" --include="*.tsx" | grep -v "node_modules" | wc -l)
if [ "$ANY_FOUND" -gt 0 ]; then
    echo "⚠️  'any' type found in frontend:"
    grep -rn ": any" frontend/src/ --include="*.ts" --include="*.tsx" | grep -v "node_modules"
fi

# Dependencies vulnérables
echo ""
cd backend && pip audit 2>/dev/null || echo "⚠️  pip audit not installed"
cd ../frontend && npm audit --production 2>/dev/null || echo "⚠️  npm audit warnings (check manually)"
```

---

## RÉSUMÉ OUTPUT

```
=== FULL TEST RESULTS ===

Lint:
  ✅ Backend (ruff)
  ✅ Frontend (eslint)

Tests:
  ✅ Backend unit: 62 passed
  ✅ Backend integration: 28 passed
  ✅ Frontend: 41 passed

Coverage:
  Backend: 74% (minimum 70%)
  Frontend: 68%

Types:
  ✅ TypeScript: no errors

Build:
  ✅ Frontend: build successful
  ✅ Backend: Docker build successful

Security:
  ✅ No secrets in code
  ✅ No print() in backend
  ⚠️  2 'any' types in frontend (fix before merge)

TOTAL: ✅ READY TO DEPLOY
```

---

## QUAND EXÉCUTER

| Situation | Commande |
|-----------|---------|
| Avant de push une PR | `/full-test` |
| Quick check pendant le dev | `/full-test quick` |
| Avant un deploy | `/full-test` (automatique via CI aussi) |
| Après un refactor | `/full-test` |
| Debug un test qui échoue | `pytest tests/path/test_file.py::test_name -xvs` |

---

## SEUILS

| Métrique | Seuil | Bloquant ? |
|----------|-------|-----------|
| Lint errors | 0 | ✅ Bloquant |
| Unit test failures | 0 | ✅ Bloquant |
| Integration test failures | 0 | ✅ Bloquant |
| Backend coverage | ≥70% | ✅ Bloquant |
| Frontend coverage | ≥60% | ⚠️ Warning |
| TypeScript errors | 0 | ✅ Bloquant |
| Build errors | 0 | ✅ Bloquant |
| Secrets in code | 0 | ✅ Bloquant |
| `any` types | 0 | ⚠️ Warning (fix before merge) |
| `print()` in backend | 0 | ⚠️ Warning |
| Dependency vulnerabilities | 0 high/critical | ⚠️ Warning |
