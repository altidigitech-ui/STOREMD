# /add-scanner — Wizard ajout d'un nouveau scanner

> **Commande slash pour créer un nouveau scanner de A à Z.**
> **Crée le fichier, l'enregistre dans le registry, crée le test.**
> **Usage : `/add-scanner`**

---

## USAGE

```
/add-scanner
→ Claude Code demande les infos et génère tout
```

---

## INFORMATIONS À FOURNIR

Claude Code pose ces questions :

```
1. Nom du scanner (snake_case) :
   Ex: "broken_links", "email_health", "hs_code_validator"

2. Module :
   ○ health
   ○ listings
   ○ agentic
   ○ compliance
   ○ browser

3. Groupe d'exécution :
   ○ shopify_api   (appelle l'API Shopify, parallèle, semaphore partagé)
   ○ external      (HTTP/DNS externe, parallèle)
   ○ browser       (Playwright, séquentiel, Pro only)

4. Plan minimum requis :
   ○ free
   ○ starter
   ○ pro

5. Description courte (1 phrase) :
   Ex: "Détecte les liens cassés internes et externes"

6. Input principal :
   Ex: "Shopify Products API", "HTTP HEAD requests", "Playwright render"

7. Output principal :
   Ex: "Liste de liens cassés avec status code et page source"
```

---

## CE QUE CLAUDE CODE GÉNÈRE

### 1. Fichier scanner

```python
# backend/app/agent/analyzers/{scanner_name}.py

from app.agent.analyzers.base import BaseScanner, ScannerResult
from app.models.scan import ScanIssue
from app.services.shopify import ShopifyClient

class {ScannerClass}(BaseScanner):
    """
    {description}
    
    Module: {module}
    Group: {group}
    Plan: {plan}+
    """

    name = "{scanner_name}"
    module = "{module}"
    group = "{group}"
    requires_plan = "{plan}"

    async def scan(
        self,
        store_id: str,
        shopify: ShopifyClient,
        memory_context: list[dict],
    ) -> ScannerResult:
        issues: list[ScanIssue] = []

        # TODO: Implémenter la logique du scanner
        # 1. Récupérer les données (Shopify API, HTTP, DNS, etc.)
        # 2. Analyser
        # 3. Créer les ScanIssues pour chaque problème détecté
        # 4. Retourner ScannerResult

        return ScannerResult(
            scanner_name=self.name,
            issues=issues,
            metrics={
                "items_checked": 0,
                "issues_found": len(issues),
            },
        )
```

### 2. Enregistrement dans le registry

```python
# backend/app/agent/analyzers/__init__.py
# Ajouter l'import et l'instance dans ScannerRegistry.__init__

from app.agent.analyzers.{scanner_name} import {ScannerClass}

# Dans la liste self._scanners :
{ScannerClass}(),    # {description}
```

### 3. Fichier test

```python
# backend/tests/test_analyzers/test_{scanner_name}.py

import pytest
from app.agent.analyzers.{scanner_name} import {ScannerClass}

@pytest.fixture
def scanner():
    return {ScannerClass}()

@pytest.fixture
def mock_shopify(mocker):
    client = mocker.AsyncMock()
    client.shop_domain = "teststore.myshopify.com"
    return client


@pytest.mark.unit
@pytest.mark.asyncio
async def test_detects_issues(scanner, mock_shopify):
    """Happy path : le scanner détecte les issues."""
    # TODO: Configurer le mock avec des données qui déclenchent des issues
    mock_shopify.graphql.return_value = {{}}  # Données avec problèmes

    result = await scanner.scan("store-1", mock_shopify, [])

    assert len(result.issues) > 0
    assert result.issues[0].module == "{module}"
    assert result.issues[0].scanner == "{scanner_name}"
    assert result.issues[0].severity in ("critical", "major", "minor", "info")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_no_issues_when_clean(scanner, mock_shopify):
    """Pas de problème détecté quand les données sont clean."""
    # TODO: Configurer le mock avec des données propres
    mock_shopify.graphql.return_value = {{}}  # Données sans problèmes

    result = await scanner.scan("store-1", mock_shopify, [])

    assert len(result.issues) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_shopify_api_error(scanner, mock_shopify):
    """Le scanner gère les erreurs Shopify API."""
    from app.core.exceptions import ShopifyError, ErrorCode

    mock_shopify.graphql.side_effect = ShopifyError(
        code=ErrorCode.SHOPIFY_API_UNAVAILABLE,
        message="Shopify down",
        status_code=503,
    )

    with pytest.raises(ShopifyError):
        await scanner.scan("store-1", mock_shopify, [])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_should_run_plan(scanner):
    """Vérifie should_run selon le plan et le module."""
    assert await scanner.should_run(["{module}"], "pro") is True
    assert await scanner.should_run(["{module}"], "agency") is True

    # Vérifier le plan minimum
    plan_hierarchy = {{"free": 0, "starter": 1, "pro": 2, "agency": 3}}
    min_plan_level = plan_hierarchy["{plan}"]

    for plan, level in plan_hierarchy.items():
        expected = level >= min_plan_level
        assert await scanner.should_run(["{module}"], plan) is expected, \
            f"should_run with plan={{plan}} should be {{expected}}"

    # Mauvais module
    assert await scanner.should_run(["wrong_module"], "pro") is False
```

### 4. Mise à jour FEATURES.md (rappel)

```
Claude Code rappelle :
"N'oublie pas d'ajouter cette feature dans docs/FEATURES.md avec :
 - Numéro (#XX)
 - Plan
 - Phase (M1 ou M2+)
 - Scanner
 - Endpoint
 - Composant frontend
 Et dans le FEATURE_PLANS dict pour le plan checking."
```

---

## CHECKLIST POST-CRÉATION

```
[ ] Scanner créé dans backend/app/agent/analyzers/{name}.py
[ ] Scanner enregistré dans ScannerRegistry (analyzers/__init__.py)
[ ] Test créé dans backend/tests/test_analyzers/test_{name}.py
[ ] 4 tests minimum : detect issues, no issues, API error, should_run plan
[ ] Scanner ajouté dans docs/FEATURES.md
[ ] FEATURE_PLANS mis à jour dans le code (plan checking)
[ ] Groupe correct (shopify_api / external / browser)
[ ] Plan correct (free / starter / pro)
[ ] Module correct (health / listings / agentic / compliance / browser)
[ ] Tests passent : pytest tests/test_analyzers/test_{name}.py -xvs
```

---

## EXEMPLES RÉELS

```
/add-scanner
  Nom: email_health
  Module: health
  Groupe: external
  Plan: pro
  Description: Vérifie SPF, DKIM, DMARC du domaine email du store
  Input: DNS lookups sur le domaine du store
  Output: Status SPF/DKIM/DMARC + recommandations

→ Génère :
  backend/app/agent/analyzers/email_health.py
  backend/tests/test_analyzers/test_email_health.py
  + update analyzers/__init__.py
  + rappel docs/FEATURES.md
```
