"""Mock Shopify API responses for testing."""

MOCK_SHOP_DATA = {
    "shop": {
        "name": "Test Store",
        "primaryDomain": {"url": "https://teststore.com", "host": "teststore.com"},
        "plan": {"displayName": "Shopify"},
        "currencyCode": "USD",
        "billingAddress": {"countryCodeV2": "US"},
    },
    "productsCount": {"count": 50},
}

MOCK_APPS_DATA = {
    "appInstallations": {
        "pageInfo": {"hasNextPage": False, "endCursor": None},
        "edges": [
            {
                "node": {
                    "app": {
                        "id": "gid://shopify/App/1",
                        "title": "Privy",
                        "handle": "privy",
                        "developerName": "Privy Inc",
                    },
                    "accessScopes": [
                        {"handle": "read_products"},
                        {"handle": "write_script_tags"},
                    ],
                }
            },
            {
                "node": {
                    "app": {
                        "id": "gid://shopify/App/2",
                        "title": "Klaviyo",
                        "handle": "klaviyo",
                        "developerName": "Klaviyo Inc",
                    },
                    "accessScopes": [
                        {"handle": "read_products"},
                        {"handle": "read_customers"},
                    ],
                }
            },
        ],
    }
}

MOCK_PRODUCTS_DATA = {
    "products": {
        "edges": [
            {
                "cursor": "cursor1",
                "node": {
                    "id": "gid://shopify/Product/123",
                    "title": "Organic Face Cream",
                    "handle": "organic-face-cream",
                    "status": "ACTIVE",
                    "productType": "skincare",
                    "descriptionHtml": "<p>Nice cream.</p>",
                    "seo": {"title": None, "description": None},
                    "images": {
                        "edges": [
                            {
                                "node": {
                                    "id": "img1",
                                    "altText": None,
                                    "url": "https://cdn.shopify.com/img1.jpg",
                                    "width": 800,
                                    "height": 800,
                                }
                            },
                            {
                                "node": {
                                    "id": "img2",
                                    "altText": "Face cream",
                                    "url": "https://cdn.shopify.com/img2.jpg",
                                    "width": 800,
                                    "height": 800,
                                }
                            },
                        ]
                    },
                    "variants": {
                        "edges": [
                            {
                                "node": {
                                    "id": "var1",
                                    "title": "Default",
                                    "sku": "FC001",
                                    "barcode": None,
                                    "price": "29.99",
                                    "inventoryQuantity": 42,
                                }
                            },
                        ]
                    },
                    "metafields": {"edges": []},
                },
            },
        ],
        "pageInfo": {"hasNextPage": False, "endCursor": "cursor1"},
    }
}

MOCK_THEME_DATA = {
    "themes": {
        "edges": [
            {
                "node": {
                    "id": "gid://shopify/Theme/1",
                    "name": "Dawn",
                    "role": "MAIN",
                }
            }
        ]
    }
}

MOCK_SCRIPT_TAGS = {
    "scriptTags": {
        "edges": [
            {
                "node": {
                    "id": "st1",
                    "src": "https://privy.com/widget.js",
                    "displayScope": "ALL",
                }
            },
            {
                "node": {
                    "id": "st2",
                    "src": "https://old-app.com/legacy.js",
                    "displayScope": "ALL",
                }
            },
        ]
    }
}

MOCK_RECURRING_CHARGES = {
    "recurring_application_charges": [
        {
            "id": 1,
            "name": "Old SEO App",
            "status": "active",
            "price": "9.99",
            "created_at": "2025-11-01T00:00:00Z",
        },
    ]
}
