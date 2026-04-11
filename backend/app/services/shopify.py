"""Shopify Admin API client — httpx async, GraphQL, rate limit handling."""

import asyncio

import httpx
import structlog

from app.config import settings
from app.core.exceptions import ErrorCode, ShopifyError
from app.core.security import decrypt_token

logger = structlog.get_logger()


class ShopifyClient:
    """Async client for the Shopify Admin GraphQL API.

    Features:
    - Semaphore (max 4 concurrent requests)
    - Retry on 429 with exponential backoff
    - Retry on 5xx server errors
    - GraphQL error detection
    """

    def __init__(self, shop_domain: str, encrypted_token: str):
        self.shop_domain = shop_domain
        self.access_token = decrypt_token(encrypted_token)
        self.api_version = settings.SHOPIFY_API_VERSION
        self.base_url = f"https://{shop_domain}/admin/api/{self.api_version}"
        self.semaphore = asyncio.Semaphore(4)

    @property
    def headers(self) -> dict[str, str]:
        return {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json",
        }

    async def graphql(self, query: str, variables: dict | None = None) -> dict:
        """Execute a GraphQL query with retry on 429 and 5xx."""
        async with self.semaphore:
            async with httpx.AsyncClient(timeout=30.0) as client:
                for attempt in range(4):  # 1 try + 3 retries
                    response = await client.post(
                        f"{self.base_url}/graphql.json",
                        json={"query": query, "variables": variables or {}},
                        headers=self.headers,
                    )

                    # Rate limit -> retry with backoff
                    if response.status_code == 429:
                        retry_after = float(response.headers.get("Retry-After", "2"))
                        wait = retry_after * (2**attempt)
                        logger.warning(
                            "shopify_rate_limit",
                            shop=self.shop_domain,
                            retry_after=wait,
                            attempt=attempt,
                        )
                        await asyncio.sleep(wait)
                        continue

                    # Server error -> retry
                    if response.status_code >= 500:
                        wait = 2**attempt
                        logger.warning(
                            "shopify_server_error",
                            shop=self.shop_domain,
                            status=response.status_code,
                        )
                        await asyncio.sleep(wait)
                        continue

                    response.raise_for_status()
                    data = response.json()

                    # GraphQL errors (HTTP 200 but errors in body)
                    if "errors" in data:
                        raise ShopifyError(
                            code=ErrorCode.SHOPIFY_GRAPHQL_ERROR,
                            message=str(data["errors"]),
                            status_code=502,
                            context={
                                "shop": self.shop_domain,
                                "query": query[:200],
                            },
                        )

                    return data["data"]

                # All retries exhausted
                raise ShopifyError(
                    code=ErrorCode.SHOPIFY_RATE_LIMIT,
                    message="Shopify API unavailable after 4 attempts",
                    status_code=429,
                    context={"shop": self.shop_domain},
                )

    async def rest_get(self, endpoint: str, params: dict | None = None) -> dict:
        """GET REST endpoint (for endpoints without GraphQL equivalent)."""
        async with self.semaphore:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/{endpoint}.json",
                    params=params,
                    headers=self.headers,
                )
                if response.status_code == 429:
                    raise ShopifyError(
                        code=ErrorCode.SHOPIFY_RATE_LIMIT,
                        message="Shopify REST API rate limited",
                        status_code=429,
                    )
                response.raise_for_status()
                return response.json()
