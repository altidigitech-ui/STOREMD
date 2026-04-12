"""OneClickFixer — the ACT layer for auto-applicable fixes.

Each method:
- Snapshots the current `before_state` for revert.
- Runs a Shopify Admin API GraphQL mutation.
- Returns `(before_state, after_state)` so the caller can persist them.

Errors surface as `ShopifyError` — callers (fixes route, Celery task)
decide whether to retry / bubble to the merchant.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from app.core.exceptions import ErrorCode, ShopifyError

if TYPE_CHECKING:
    from app.services.shopify import ShopifyClient

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# GraphQL mutations
# ---------------------------------------------------------------------------


_PRODUCT_IMAGE_LOOKUP = """
query ProductImageLookup($id: ID!) {
  product(id: $id) {
    id
    images(first: 50) {
      edges { node { id altText url } }
    }
  }
}
"""

_PRODUCT_IMAGE_UPDATE = """
mutation ProductImageUpdate($productId: ID!, $image: ImageInput!) {
  productImageUpdate(productId: $productId, image: $image) {
    image { id altText }
    userErrors { field message }
  }
}
"""


_METAFIELD_LOOKUP = """
query MetafieldLookup($ownerId: ID!, $namespace: String!, $key: String!) {
  product(id: $ownerId) {
    metafield(namespace: $namespace, key: $key) { id value type }
  }
}
"""

_METAFIELDS_SET = """
mutation MetafieldsSet($metafields: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $metafields) {
    metafields { id namespace key value type }
    userErrors { field message }
  }
}
"""


_URL_REDIRECT_CREATE = """
mutation UrlRedirectCreate($urlRedirect: UrlRedirectInput!) {
  urlRedirectCreate(urlRedirect: $urlRedirect) {
    urlRedirect { id path target }
    userErrors { field message }
  }
}
"""


_SCRIPT_TAG_LOOKUP = """
query ScriptTagLookup($id: ID!) {
  node(id: $id) {
    ... on ScriptTag { id src displayScope }
  }
}
"""

_SCRIPT_TAG_DELETE = """
mutation ScriptTagDelete($id: ID!) {
  scriptTagDelete(id: $id) {
    deletedScriptTagId
    userErrors { field message }
  }
}
"""


_PRODUCT_DESCRIPTION_LOOKUP = """
query ProductDescriptionLookup($id: ID!) {
  product(id: $id) { id descriptionHtml }
}
"""

_PRODUCT_UPDATE_DESCRIPTION = """
mutation ProductUpdateDescription($input: ProductInput!) {
  productUpdate(input: $input) {
    product { id descriptionHtml }
    userErrors { field message }
  }
}
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _raise_on_user_errors(payload: dict, op: str) -> None:
    """Convert Shopify `userErrors` blocks into ShopifyError."""
    errors = payload.get("userErrors") or []
    if not errors:
        return
    messages = "; ".join(
        f"{e.get('field') or ''}: {e.get('message') or ''}".strip(": ")
        for e in errors
    )
    raise ShopifyError(
        code=ErrorCode.SHOPIFY_GRAPHQL_ERROR,
        message=f"{op} failed: {messages}",
        status_code=502,
        context={"op": op, "errors": errors},
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class OneClickFixer:
    """Wraps Shopify Admin API mutations used by the fixes route."""

    def __init__(self, shopify: ShopifyClient) -> None:
        self.shopify = shopify

    # -- Alt text --------------------------------------------------------

    async def apply_alt_text(
        self, product_id: str, image_id: str, alt_text: str
    ) -> tuple[dict, dict]:
        """Update an image's alt text. Returns (before, after)."""
        before = {"alt_text": None}
        try:
            lookup = await self.shopify.graphql(
                _PRODUCT_IMAGE_LOOKUP, {"id": product_id}
            )
            images = (
                lookup.get("product", {}).get("images", {}).get("edges", [])
            )
            for edge in images:
                node = edge["node"]
                if node["id"] == image_id:
                    before = {"alt_text": node.get("altText")}
                    break
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "alt_text_before_lookup_failed",
                product_id=product_id,
                image_id=image_id,
                error=str(exc),
            )

        data = await self.shopify.graphql(
            _PRODUCT_IMAGE_UPDATE,
            {
                "productId": product_id,
                "image": {"id": image_id, "altText": alt_text},
            },
        )
        payload = data.get("productImageUpdate", {}) or {}
        _raise_on_user_errors(payload, "productImageUpdate")

        after = {"alt_text": alt_text}
        logger.info(
            "one_click_fix_alt_text",
            product_id=product_id,
            image_id=image_id,
        )
        return before, after

    # -- Metafield -------------------------------------------------------

    async def apply_metafield(
        self,
        owner_id: str,
        namespace: str,
        key: str,
        value: str,
        type_: str = "single_line_text_field",
    ) -> tuple[dict, dict]:
        """Set a product metafield. `owner_id` is a Product GID."""
        before: dict = {
            "metafield": {"namespace": namespace, "key": key, "value": None},
        }
        try:
            lookup = await self.shopify.graphql(
                _METAFIELD_LOOKUP,
                {"ownerId": owner_id, "namespace": namespace, "key": key},
            )
            existing = (lookup.get("product") or {}).get("metafield") or {}
            before["metafield"]["value"] = existing.get("value")
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "metafield_before_lookup_failed",
                owner_id=owner_id,
                namespace=namespace,
                key=key,
                error=str(exc),
            )

        data = await self.shopify.graphql(
            _METAFIELDS_SET,
            {
                "metafields": [
                    {
                        "ownerId": owner_id,
                        "namespace": namespace,
                        "key": key,
                        "value": value,
                        "type": type_,
                    }
                ]
            },
        )
        payload = data.get("metafieldsSet", {}) or {}
        _raise_on_user_errors(payload, "metafieldsSet")

        after = {
            "metafield": {
                "namespace": namespace,
                "key": key,
                "value": value,
                "type": type_,
            }
        }
        logger.info(
            "one_click_fix_metafield",
            owner_id=owner_id,
            namespace=namespace,
            key=key,
        )
        return before, after

    # -- Redirect --------------------------------------------------------

    async def apply_redirect(
        self, from_path: str, to_path: str
    ) -> tuple[dict, dict]:
        """Create a URL redirect from a broken path to a live one."""
        before = {"redirect": None}

        data = await self.shopify.graphql(
            _URL_REDIRECT_CREATE,
            {
                "urlRedirect": {
                    "path": from_path,
                    "target": to_path,
                }
            },
        )
        payload = data.get("urlRedirectCreate", {}) or {}
        _raise_on_user_errors(payload, "urlRedirectCreate")

        created = payload.get("urlRedirect") or {}
        after = {
            "redirect": {
                "id": created.get("id"),
                "path": created.get("path", from_path),
                "target": created.get("target", to_path),
            }
        }
        logger.info(
            "one_click_fix_redirect",
            from_path=from_path,
            to_path=to_path,
        )
        return before, after

    # -- Residue script removal ------------------------------------------

    async def remove_residue_script(
        self, script_tag_id: str
    ) -> tuple[dict, dict]:
        """Delete a script tag left over by an uninstalled app."""
        before: dict = {"script_tag": {"id": script_tag_id}}
        try:
            lookup = await self.shopify.graphql(
                _SCRIPT_TAG_LOOKUP, {"id": script_tag_id}
            )
            node = lookup.get("node") or {}
            if node:
                before["script_tag"] = {
                    "id": node.get("id", script_tag_id),
                    "src": node.get("src"),
                    "displayScope": node.get("displayScope"),
                }
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "residue_script_before_lookup_failed",
                script_tag_id=script_tag_id,
                error=str(exc),
            )

        data = await self.shopify.graphql(
            _SCRIPT_TAG_DELETE, {"id": script_tag_id}
        )
        payload = data.get("scriptTagDelete", {}) or {}
        _raise_on_user_errors(payload, "scriptTagDelete")

        after = {"deleted_script_tag_id": payload.get("deletedScriptTagId")}
        logger.info(
            "one_click_fix_remove_residue",
            script_tag_id=script_tag_id,
        )
        return before, after

    # -- Product description rewrite -------------------------------------

    async def rewrite_description(
        self, product_id: str, new_description_html: str
    ) -> tuple[dict, dict]:
        """Overwrite a product's HTML description."""
        before = {"description_html": None}
        try:
            lookup = await self.shopify.graphql(
                _PRODUCT_DESCRIPTION_LOOKUP, {"id": product_id}
            )
            product = lookup.get("product") or {}
            before["description_html"] = product.get("descriptionHtml")
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "description_before_lookup_failed",
                product_id=product_id,
                error=str(exc),
            )

        data = await self.shopify.graphql(
            _PRODUCT_UPDATE_DESCRIPTION,
            {
                "input": {
                    "id": product_id,
                    "descriptionHtml": new_description_html,
                }
            },
        )
        payload = data.get("productUpdate", {}) or {}
        _raise_on_user_errors(payload, "productUpdate")

        after = {"description_html": new_description_html}
        logger.info(
            "one_click_fix_rewrite_description",
            product_id=product_id,
        )
        return before, after
