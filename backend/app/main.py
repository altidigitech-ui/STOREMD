"""FastAPI application — StoreMD backend."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import structlog

from app.config import settings
from app.core.exceptions import AppError, ErrorCode
from app.core.logging import setup_logging

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

setup_logging(settings.APP_ENV)
logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Sentry
# ---------------------------------------------------------------------------

if settings.SENTRY_DSN and settings.is_production:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[StarletteIntegration(), FastApiIntegration()],
        traces_sample_rate=0.1,
        environment=settings.APP_ENV,
    )

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="StoreMD API",
    version=settings.APP_VERSION,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url=None,
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.APP_URL,
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handler pour toutes les erreurs metier."""
    logger.error(
        "app_error",
        code=exc.code.value,
        message=exc.message,
        status_code=exc.status_code,
        path=request.url.path,
        **exc.context,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handler pour les erreurs de validation Pydantic."""
    logger.warning(
        "validation_error",
        path=request.url.path,
        errors=str(exc.errors()),
    )
    # Sanitize errors: remove non-serializable ctx values
    errors = []
    for err in exc.errors():
        clean_err = {k: v for k, v in err.items() if k != "ctx"}
        errors.append(clean_err)

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": ErrorCode.VALIDATION_ERROR.value,
                "message": "Validation failed",
                "details": errors,
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler catch-all pour les erreurs non gerees."""
    logger.exception(
        "unhandled_error",
        path=request.url.path,
        error_type=type(exc).__name__,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": ErrorCode.INTERNAL_ERROR.value,
                "message": "An unexpected error occurred",
            }
        },
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

from app.api.routes.health import router as health_router  # noqa: E402
from app.api.routes.auth import router as auth_router  # noqa: E402
from app.api.routes.scans import router as scans_router  # noqa: E402
from app.api.routes.stores import router as stores_router  # noqa: E402

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(scans_router)
app.include_router(stores_router)
