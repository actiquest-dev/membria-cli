"""Webhook server: FastAPI server for receiving GitHub and CI webhooks."""

import logging
from typing import Optional, Dict, Any

from membria.webhook_handler import WebhookHandler
from membria.outcome_tracker import OutcomeTracker

logger = logging.getLogger(__name__)


class WebhookServer:
    """Webhook server for receiving and processing events."""

    def __init__(self, port: int = 8000, host: str = "127.0.0.1"):
        """Initialize webhook server.

        Args:
            port: Server port
            host: Server host
        """
        self.port = port
        self.host = host
        self.handler = WebhookHandler()
        self.tracker = OutcomeTracker()
        self._app = None

    def _create_app(self):
        """Create FastAPI app (lazy import to avoid hard dependency)."""
        try:
            from fastapi import FastAPI, Request, Header, JSONResponse
            from fastapi.responses import JSONResponse as FastAPIJSONResponse

            app = FastAPI(title="Membria Webhook Server")

            @app.post("/github/push")
            async def github_push(request: Request):
                """Handle GitHub push webhook."""
                raw_body = await request.body()
                payload = await request.json()
                signature = request.headers.get("X-Hub-Signature-256")

                result = self.handler.process_webhook(
                    "push",
                    payload,
                    signature,
                    raw_body=raw_body,
                )

                return FastAPIJSONResponse(result)

            @app.post("/github/pull_request")
            async def github_pull_request(request: Request):
                """Handle GitHub pull request webhook."""
                raw_body = await request.body()
                payload = await request.json()
                signature = request.headers.get("X-Hub-Signature-256")

                result = self.handler.process_webhook(
                    "pull_request",
                    payload,
                    signature,
                    raw_body=raw_body,
                )

                return FastAPIJSONResponse(result)

            @app.post("/github/workflow_run")
            async def github_workflow_run(request: Request):
                """Handle GitHub Actions workflow_run webhook."""
                raw_body = await request.body()
                payload = await request.json()
                signature = request.headers.get("X-Hub-Signature-256")

                result = self.handler.process_webhook(
                    "workflow_run",
                    payload,
                    signature,
                    raw_body=raw_body,
                )

                return FastAPIJSONResponse(result)

            @app.post("/github/check_run")
            async def github_check_run(request: Request):
                """Handle GitHub check_run webhook."""
                raw_body = await request.body()
                payload = await request.json()
                signature = request.headers.get("X-Hub-Signature-256")

                result = self.handler.process_webhook(
                    "check_run",
                    payload,
                    signature,
                    raw_body=raw_body,
                )

                return FastAPIJSONResponse(result)

            @app.post("/ci/event")
            async def ci_event(request: Request):
                """Handle generic CI event (JSON)."""
                payload = await request.json()

                result = self.handler.process_webhook(
                    "ci_json",
                    payload,
                )

                return FastAPIJSONResponse(result)

            @app.get("/health")
            async def health():
                """Health check endpoint."""
                return FastAPIJSONResponse({"status": "healthy"})

            return app

        except ImportError:
            logger.error("FastAPI not installed. Install with: pip install fastapi uvicorn")
            return None

    def get_app(self):
        """Get FastAPI app instance."""
        if not self._app:
            self._app = self._create_app()
        return self._app

    def run(self):
        """Run the webhook server."""
        app = self.get_app()
        if not app:
            logger.error("Failed to create FastAPI app")
            return

        try:
            import uvicorn

            logger.info(f"Starting Membria webhook server on {self.host}:{self.port}")
            uvicorn.run(app, host=self.host, port=self.port)

        except ImportError:
            logger.error("Uvicorn not installed. Install with: pip install uvicorn")


def create_webhook_server(port: int = 8000, host: str = "127.0.0.1") -> WebhookServer:
    """Factory function to create webhook server.

    Args:
        port: Server port
        host: Server host

    Returns:
        WebhookServer instance
    """
    return WebhookServer(port=port, host=host)
