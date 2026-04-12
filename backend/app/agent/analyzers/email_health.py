"""Email Domain Health Scanner — Feature #20.

DNS checks (SPF, DKIM, DMARC) on the store's sending domain. All DNS
queries run in a thread executor so we stay async-friendly.
"""

from __future__ import annotations

import asyncio
import socket
from typing import TYPE_CHECKING

import structlog

from app.agent.analyzers.base import BaseScanner, ScannerResult
from app.models.scan import ScanIssue

if TYPE_CHECKING:
    from app.services.shopify import ShopifyClient

logger = structlog.get_logger()


SHOP_QUERY = """
query {
  shop {
    email
    primaryDomain { host url }
  }
}
"""

# DKIM selectors we probe in order. Many stores use "google" or a
# provider-specific selector; "default" is the fallback.
_DKIM_SELECTORS: tuple[str, ...] = ("default", "google", "selector1", "k1")


class EmailHealthScanner(BaseScanner):
    """Check SPF / DKIM / DMARC records on the store's sending domain."""

    name = "email_health"
    module = "health"
    group = "external"
    requires_plan = "pro"

    async def scan(
        self,
        store_id: str,
        shopify: ShopifyClient,
        memory_context: list[dict],
    ) -> ScannerResult:
        domain = await self._resolve_domain(shopify)
        if not domain:
            return ScannerResult(
                scanner_name=self.name,
                issues=[],
                metrics={
                    "domain": None,
                    "skipped": "no_domain",
                    "spf_found": False,
                    "dkim_found": False,
                    "dmarc_found": False,
                },
            )

        spf_found = await self._check_spf(domain)
        dkim_found = await self._check_dkim(domain)
        dmarc_found = await self._check_dmarc(domain)

        issues: list[ScanIssue] = []

        if not spf_found:
            issues.append(
                ScanIssue(
                    module="health",
                    scanner=self.name,
                    severity="major",
                    title=f"SPF record missing on {domain}",
                    description=(
                        "No SPF record found. Spoofed emails sent from your "
                        "domain will land in spam (or be rejected)."
                    ),
                    impact="Emails may land in spam / be rejected",
                    impact_value=None,
                    impact_unit=None,
                    fix_type="manual",
                    fix_description=(
                        'Add a TXT record at the root of your domain: '
                        '"v=spf1 include:spf.shopify.com ~all".'
                    ),
                    auto_fixable=False,
                    context={"domain": domain, "check": "spf"},
                )
            )

        if not dkim_found:
            issues.append(
                ScanIssue(
                    module="health",
                    scanner=self.name,
                    severity="minor",
                    title=f"DKIM signature not detected on {domain}",
                    description=(
                        "No DKIM selectors resolved (tested: "
                        + ", ".join(_DKIM_SELECTORS)
                        + "). Recipients can't verify your emails' origin."
                    ),
                    fix_type="manual",
                    fix_description=(
                        "Enable DKIM in Shopify Email / your ESP and publish "
                        "the TXT record in DNS."
                    ),
                    auto_fixable=False,
                    context={"domain": domain, "check": "dkim"},
                )
            )

        if not dmarc_found:
            issues.append(
                ScanIssue(
                    module="health",
                    scanner=self.name,
                    severity="minor",
                    title=f"DMARC policy missing on {domain}",
                    description=(
                        "No DMARC record at _dmarc.{domain}. Without DMARC "
                        "you can't instruct mail servers how to handle "
                        "failed SPF/DKIM checks."
                    ).format(domain=domain),
                    fix_type="manual",
                    fix_description=(
                        'Publish a TXT record at "_dmarc.{domain}" with at '
                        'least "v=DMARC1; p=none; rua=mailto:you@{domain}".'
                    ).format(domain=domain),
                    auto_fixable=False,
                    context={"domain": domain, "check": "dmarc"},
                )
            )

        deliverability_risk = "low"
        if not spf_found:
            deliverability_risk = "high"
        elif not dkim_found or not dmarc_found:
            deliverability_risk = "medium"

        logger.info(
            "email_health_scan_complete",
            store_id=store_id,
            domain=domain,
            spf=spf_found,
            dkim=dkim_found,
            dmarc=dmarc_found,
        )

        return ScannerResult(
            scanner_name=self.name,
            issues=issues,
            metrics={
                "domain": domain,
                "spf_found": spf_found,
                "dkim_found": dkim_found,
                "dmarc_found": dmarc_found,
                "deliverability_risk": deliverability_risk,
            },
        )

    # ------------------------------------------------------------------
    # Domain resolution
    # ------------------------------------------------------------------

    async def _resolve_domain(self, shopify: ShopifyClient) -> str | None:
        try:
            data = await shopify.graphql(SHOP_QUERY)
        except Exception as exc:  # noqa: BLE001
            logger.warning("email_health_shop_query_failed", error=str(exc))
            return None

        shop = (data or {}).get("shop") or {}

        # Prefer the merchant-configured primary domain host (e.g. "mystore.com").
        primary = (shop.get("primaryDomain") or {}).get("host")
        if primary:
            return primary.lower().strip()

        email = shop.get("email") or ""
        if "@" in email:
            return email.split("@", 1)[1].lower().strip()

        return None

    # ------------------------------------------------------------------
    # DNS checks — sync calls wrapped in executor
    # ------------------------------------------------------------------

    @staticmethod
    async def _txt_records(fqdn: str) -> list[str]:
        """Return the TXT records for `fqdn`, or [] on any DNS error."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _query_txt, fqdn)

    async def _check_spf(self, domain: str) -> bool:
        records = await self._txt_records(domain)
        return any(r.lower().startswith("v=spf1") for r in records)

    async def _check_dkim(self, domain: str) -> bool:
        for selector in _DKIM_SELECTORS:
            records = await self._txt_records(f"{selector}._domainkey.{domain}")
            if any("v=dkim1" in r.lower() for r in records):
                return True
            # Some DKIM records omit "v=DKIM1" but include "k=" or "p=".
            if any(
                ("k=" in r and "p=" in r) for r in (x.lower() for x in records)
            ):
                return True
        return False

    async def _check_dmarc(self, domain: str) -> bool:
        records = await self._txt_records(f"_dmarc.{domain}")
        return any(r.lower().startswith("v=dmarc1") for r in records)


def _query_txt(fqdn: str) -> list[str]:
    """Sync DNS TXT query using dnspython if available, falling back to
    socket.getaddrinfo for a presence signal.

    Returns a list of decoded TXT records. Any error returns [].
    """
    # Prefer dnspython (comes transitively via Mem0 / httpx dependencies
    # in many setups but may be absent).
    try:
        import dns.resolver  # type: ignore[import-not-found]

        resolver = dns.resolver.Resolver()
        resolver.lifetime = 5.0
        answer = resolver.resolve(fqdn, "TXT")
        out: list[str] = []
        for rdata in answer:
            # dnspython returns TXT as a sequence of bytes chunks.
            try:
                strings = rdata.strings  # type: ignore[attr-defined]
                out.append(b"".join(strings).decode("utf-8", errors="replace"))
            except Exception:  # noqa: BLE001
                out.append(str(rdata).strip('"'))
        return out
    except ModuleNotFoundError:
        pass
    except Exception:  # noqa: BLE001
        return []

    # Fallback: we can't read TXT content via stdlib, but we can at least
    # tell if the name resolves at all. That's a weak signal, so be
    # conservative and return [].
    try:
        socket.gethostbyname(fqdn)
    except OSError:
        return []
    return []
