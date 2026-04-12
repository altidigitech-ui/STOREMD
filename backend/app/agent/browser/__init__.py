"""Browser scanners — Playwright-powered analysis (Pro plan).

Lives in the Celery worker (Dockerfile.worker installs Chromium).
Scanners run sequentially because Playwright is RAM-heavy.
"""
