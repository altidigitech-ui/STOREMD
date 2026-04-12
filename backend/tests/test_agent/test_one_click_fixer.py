"""Unit tests for the OneClickFixer."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from app.agent.actors.one_click_fixer import OneClickFixer
from app.core.exceptions import ShopifyError


@pytest.fixture
def shopify():
    return AsyncMock()


@pytest.fixture
def fixer(shopify):
    return OneClickFixer(shopify)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_alt_text_calls_mutation(
    fixer: OneClickFixer, shopify: AsyncMock
) -> None:
    """apply_alt_text() must fire productImageUpdate with the new alt text
    and capture the previous alt in before_state."""
    shopify.graphql.side_effect = [
        # lookup
        {
            "product": {
                "id": "gid://shopify/Product/1",
                "images": {
                    "edges": [
                        {
                            "node": {
                                "id": "gid://shopify/ProductImage/10",
                                "altText": None,
                                "url": "https://cdn.shopify.com/x.png",
                            }
                        }
                    ]
                },
            }
        },
        # mutation response
        {
            "productImageUpdate": {
                "image": {
                    "id": "gid://shopify/ProductImage/10",
                    "altText": "Organic face cream in glass jar",
                },
                "userErrors": [],
            }
        },
    ]

    before, after = await fixer.apply_alt_text(
        product_id="gid://shopify/Product/1",
        image_id="gid://shopify/ProductImage/10",
        alt_text="Organic face cream in glass jar",
    )

    assert before == {"alt_text": None}
    assert after == {"alt_text": "Organic face cream in glass jar"}
    # The second graphql call is the mutation.
    second_call = shopify.graphql.await_args_list[1]
    assert "productImageUpdate" in second_call.args[0]
    assert second_call.args[1]["productId"] == "gid://shopify/Product/1"
    assert (
        second_call.args[1]["image"]["altText"]
        == "Organic face cream in glass jar"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_metafield_snapshots_before_state(
    fixer: OneClickFixer, shopify: AsyncMock
) -> None:
    """Before-state must include the existing metafield value."""
    shopify.graphql.side_effect = [
        # lookup — existing value present
        {
            "product": {
                "metafield": {
                    "id": "gid://shopify/Metafield/9",
                    "value": "polyester",
                    "type": "single_line_text_field",
                }
            }
        },
        # mutation
        {
            "metafieldsSet": {
                "metafields": [
                    {
                        "id": "gid://shopify/Metafield/9",
                        "namespace": "custom",
                        "key": "material",
                        "value": "100% organic cotton",
                        "type": "single_line_text_field",
                    }
                ],
                "userErrors": [],
            }
        },
    ]

    before, after = await fixer.apply_metafield(
        owner_id="gid://shopify/Product/1",
        namespace="custom",
        key="material",
        value="100% organic cotton",
    )

    assert before["metafield"]["value"] == "polyester"
    assert after["metafield"]["value"] == "100% organic cotton"
    assert after["metafield"]["namespace"] == "custom"
    assert after["metafield"]["key"] == "material"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_redirect_creates_url_redirect(
    fixer: OneClickFixer, shopify: AsyncMock
) -> None:
    shopify.graphql.return_value = {
        "urlRedirectCreate": {
            "urlRedirect": {
                "id": "gid://shopify/UrlRedirect/42",
                "path": "/products/old-name",
                "target": "/products/new-name",
            },
            "userErrors": [],
        }
    }

    before, after = await fixer.apply_redirect(
        from_path="/products/old-name",
        to_path="/products/new-name",
    )

    assert before == {"redirect": None}
    assert after["redirect"]["id"] == "gid://shopify/UrlRedirect/42"
    assert after["redirect"]["path"] == "/products/old-name"
    assert after["redirect"]["target"] == "/products/new-name"

    call = shopify.graphql.await_args
    assert "urlRedirectCreate" in call.args[0]
    assert call.args[1]["urlRedirect"]["path"] == "/products/old-name"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mutation_user_errors_raise_shopify_error(
    fixer: OneClickFixer, shopify: AsyncMock
) -> None:
    """User errors in the mutation response should raise ShopifyError."""
    shopify.graphql.side_effect = [
        # lookup OK
        {"product": {"id": "gid://shopify/Product/1", "images": {"edges": []}}},
        # mutation returns userErrors
        {
            "productImageUpdate": {
                "image": None,
                "userErrors": [
                    {"field": ["image"], "message": "Image not found"}
                ],
            }
        },
    ]

    with pytest.raises(ShopifyError) as exc_info:
        await fixer.apply_alt_text(
            product_id="gid://shopify/Product/1",
            image_id="gid://shopify/ProductImage/999",
            alt_text="alt",
        )

    assert "productImageUpdate" in exc_info.value.message


@pytest.mark.unit
@pytest.mark.asyncio
async def test_remove_residue_script(
    fixer: OneClickFixer, shopify: AsyncMock
) -> None:
    shopify.graphql.side_effect = [
        # lookup
        {
            "node": {
                "id": "gid://shopify/ScriptTag/5",
                "src": "https://privy.com/widget.js",
                "displayScope": "ALL",
            }
        },
        # delete
        {
            "scriptTagDelete": {
                "deletedScriptTagId": "gid://shopify/ScriptTag/5",
                "userErrors": [],
            }
        },
    ]

    before, after = await fixer.remove_residue_script(
        script_tag_id="gid://shopify/ScriptTag/5"
    )

    assert before["script_tag"]["src"] == "https://privy.com/widget.js"
    assert after["deleted_script_tag_id"] == "gid://shopify/ScriptTag/5"
