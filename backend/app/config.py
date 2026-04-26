"""Pydantic BaseSettings — charge TOUTES les env vars depuis .env ou l'environnement."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # === App ===
    APP_ENV: str = "development"
    APP_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"
    APP_VERSION: str = "0.1.0"

    # === Supabase ===
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWT_SECRET: str = ""

    # === Shopify ===
    SHOPIFY_API_KEY: str
    SHOPIFY_API_SECRET: str
    SHOPIFY_API_VERSION: str = "2026-01"
    # NOTE: Adding write scopes requires existing merchants to re-install the app
    # to grant the new permissions via the Shopify OAuth consent screen.
    SHOPIFY_SCOPES: str = (
        "read_products,write_products,"
        "read_themes,"
        "read_orders,"
        "read_script_tags,write_script_tags,"
        "read_url_redirects,write_url_redirects"
    )

    # === Stripe ===
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_STARTER: str = ""
    STRIPE_PRICE_PRO: str = ""
    STRIPE_PRICE_AGENCY: str = ""

    # === Claude API ===
    ANTHROPIC_API_KEY: str = ""

    # === Mem0 ===
    MEM0_API_KEY: str = ""

    # === Redis ===
    REDIS_URL: str = "redis://localhost:6379/0"

    # === Resend ===
    RESEND_API_KEY: str = ""

    # === Sentry ===
    SENTRY_DSN: str = ""

    # === LangSmith ===
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_PROJECT: str = "storemd"

    # === VAPID (Push notifications) ===
    VAPID_PUBLIC_KEY: str = ""
    VAPID_PRIVATE_KEY: str = ""
    VAPID_CONTACT_EMAIL: str = "contact@storemd.com"

    # === Security ===
    FERNET_KEY: str

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_test(self) -> bool:
        return self.APP_ENV == "test"


settings = Settings()  # type: ignore[call-arg]
