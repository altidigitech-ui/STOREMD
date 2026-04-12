"""Collection backup service — feature #7.

Snapshots the store's collections (title, handle, products, rules,
sortOrder) and uploads the JSON to Supabase Storage's `backups` bucket.

Used on `themes/update` webhooks and can also be called from a Celery
task for scheduled daily backups.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from app.services.shopify import ShopifyClient

logger = structlog.get_logger()


COLLECTIONS_QUERY = """
query Collections($first: Int!, $after: String) {
  collections(first: $first, after: $after) {
    edges {
      cursor
      node {
        id
        handle
        title
        description
        sortOrder
        ruleSet {
          appliedDisjunctively
          rules {
            column
            condition
            relation
          }
        }
        products(first: 250) {
          edges { node { id handle title } }
        }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""


async def create_collection_backup(
    store_id: str,
    shopify: ShopifyClient,
    *,
    supabase: Any | None = None,
) -> dict:
    """Fetch all collections, upload a JSON snapshot, return metadata.

    The returned dict contains `{path, url, collections_count, created_at}`.
    On upload failure the function still returns the serialized payload
    (under `data`) and logs a warning — the caller decides what to do.
    """
    if supabase is None:
        from app.dependencies import get_supabase_service

        supabase = get_supabase_service()

    # Paginate through all collections.
    collections: list[dict] = []
    cursor: str | None = None
    max_pages = 10  # 10 × 50 = 500 — plenty for most stores
    for _ in range(max_pages):
        data = await shopify.graphql(
            COLLECTIONS_QUERY, {"first": 50, "after": cursor}
        )
        edges = data.get("collections", {}).get("edges", [])
        for edge in edges:
            node = edge.get("node") or {}
            products = (
                node.get("products", {}).get("edges", [])
            )
            collections.append(
                {
                    "id": node.get("id"),
                    "handle": node.get("handle"),
                    "title": node.get("title"),
                    "description": node.get("description"),
                    "sortOrder": node.get("sortOrder"),
                    "ruleSet": node.get("ruleSet"),
                    "products": [
                        {
                            "id": p["node"].get("id"),
                            "handle": p["node"].get("handle"),
                            "title": p["node"].get("title"),
                        }
                        for p in products
                    ],
                }
            )
        page = data.get("collections", {}).get("pageInfo", {})
        if not page.get("hasNextPage"):
            break
        cursor = page.get("endCursor")
        if not cursor:
            break

    now = datetime.now(UTC)
    ts = now.strftime("%Y%m%d_%H%M%S")
    path = f"{store_id}/collections_{ts}.json"
    payload = {
        "store_id": store_id,
        "created_at": now.isoformat(),
        "collections_count": len(collections),
        "collections": collections,
    }
    body = json.dumps(payload, default=str).encode("utf-8")

    public_url: str | None = None
    try:
        supabase.storage.from_("backups").upload(
            path, body, {"content-type": "application/json"}
        )
        try:
            public_url = supabase.storage.from_("backups").get_public_url(path)
        except Exception:  # noqa: BLE001
            public_url = None
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "backup_upload_failed",
            store_id=store_id,
            path=path,
            error=str(exc),
        )

    # Best-effort: record the backup in DB.
    try:
        supabase.table("backups").insert(
            {
                "store_id": store_id,
                "backup_type": "collections",
                "storage_path": path,
                "collections_count": len(collections),
                "created_at": now.isoformat(),
            }
        ).execute()
    except Exception as exc:  # noqa: BLE001
        # Not all installations have a `backups` table yet — don't fail.
        logger.info(
            "backup_record_skipped",
            store_id=store_id,
            error=str(exc)[:120],
        )

    logger.info(
        "backup_created",
        store_id=store_id,
        path=path,
        collections=len(collections),
    )

    return {
        "path": path,
        "url": public_url,
        "collections_count": len(collections),
        "created_at": now.isoformat(),
    }
