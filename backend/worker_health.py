"""Tiny HTTP healthcheck sidecar for the Celery worker container.

Railway requires a successful HTTP healthcheck to mark a deployment
healthy. Celery doesn't speak HTTP, so we run this 10-line server in
the background alongside the worker process.
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
import os


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 — http.server API
        if self.path == "/api/v1/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"healthy","role":"worker"}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *_args: object) -> None:  # noqa: ARG002
        return


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    HTTPServer(("0.0.0.0", port), HealthHandler).serve_forever()
