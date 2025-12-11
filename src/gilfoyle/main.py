"""FastAPI application for Gilfoyle AI Agent."""

import logging
import sys
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from gilfoyle import __version__
from gilfoyle.agent.gilfoyle import create_agent
from gilfoyle.config import Settings, get_settings
from gilfoyle.webhooks.handlers import WebhookHandler
from gilfoyle.webhooks.validators import validate_gitlab_signature, validate_webhook_payload

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        settings: Optional settings instance. If not provided, uses get_settings().

    Returns:
        The configured FastAPI application.
    """
    if settings is None:
        settings = get_settings()

    # Configure logging level from settings
    logging.getLogger().setLevel(settings.log_level)

    # Create the agent and handler
    agent = create_agent(settings)
    webhook_handler = WebhookHandler(settings, agent)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):  # type: ignore
        """Application lifespan handler."""
        logger.info(f"Starting {settings.app_name} v{__version__}")
        yield
        logger.info(f"Shutting down {settings.app_name}")
        await agent.close()

    app = FastAPI(
        title=settings.app_name,
        description="AI-powered GitLab MR review agent using Pydantic AI",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # Store references for use in routes
    app.state.settings = settings
    app.state.agent = agent
    app.state.webhook_handler = webhook_handler

    # Register routes
    register_routes(app)

    return app


def register_routes(app: FastAPI) -> None:
    """Register all routes on the application."""

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        """Root endpoint."""
        return {
            "name": app.state.settings.app_name,
            "version": __version__,
            "status": "running",
        }

    @app.get("/health")
    async def health_check() -> dict[str, Any]:
        """Health check endpoint.

        Returns:
            Health status information.
        """
        return {
            "status": "healthy",
            "version": __version__,
            "app_name": app.state.settings.app_name,
        }

    @app.get("/ready")
    async def readiness_check() -> dict[str, Any]:
        """Readiness check endpoint.

        Verifies that the application is ready to handle requests.
        """
        # TODO: Add actual readiness checks (e.g., GitLab connectivity)
        return {
            "status": "ready",
            "version": __version__,
        }

    @app.post("/webhook/gitlab")
    async def gitlab_webhook(
        request: Request,
        x_gitlab_token: str | None = Header(None, alias="X-Gitlab-Token"),
        x_gitlab_event: str | None = Header(None, alias="X-Gitlab-Event"),  # noqa: ARG001
    ) -> JSONResponse:
        """Handle GitLab webhook events.

        This endpoint receives webhook events from GitLab and triggers
        code reviews when Gilfoyle is mentioned or assigned as a reviewer.

        Args:
            request: The incoming request.
            x_gitlab_token: The webhook secret token.
            x_gitlab_event: The type of GitLab event.

        Returns:
            JSON response with processing status.
        """
        settings: Settings = app.state.settings
        handler: WebhookHandler = app.state.webhook_handler

        # Get raw body for signature validation
        body = await request.body()

        # Validate signature
        if not validate_gitlab_signature(body, x_gitlab_token, settings):
            logger.warning("Invalid webhook signature received")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )

        # Parse payload
        try:
            payload = await request.json()
        except Exception as e:
            logger.error(f"Failed to parse webhook payload: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload",
            ) from e

        # Validate payload structure
        is_valid, error_message = validate_webhook_payload(payload)
        if not is_valid:
            logger.debug(f"Ignoring invalid payload: {error_message}")
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"status": "ignored", "reason": error_message},
            )

        # Log the event
        event_type = payload.get("object_kind", "unknown")
        project_name = payload.get("project", {}).get("path_with_namespace", "unknown")
        logger.info(f"Received {event_type} event from {project_name}")

        # Handle the event
        try:
            result = await handler.handle_event(payload)
            return JSONResponse(status_code=status.HTTP_200_OK, content=result)
        except Exception as e:
            logger.exception(f"Error handling webhook event: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"status": "error", "message": str(e)},
            )

    @app.post("/webhook/test")
    async def test_webhook(request: Request) -> dict[str, Any]:
        """Test endpoint to verify webhook connectivity.

        This endpoint doesn't require authentication and is useful
        for testing that the server is reachable.
        """
        if not app.state.settings.debug:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Not found",
            )

        payload = await request.json() if await request.body() else {}
        return {
            "status": "received",
            "payload_keys": list(payload.keys()) if payload else [],
            "message": "Webhook test endpoint is working",
        }


# Create the default application instance
app = create_app()


def run() -> None:
    """Run the application with uvicorn.

    This is the entry point for the `gilfoyle` console script.
    """
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "gilfoyle.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    run()
