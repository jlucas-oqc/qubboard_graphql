"""
Root and health-check routes for the qupboard_graphql service.

Provides a ``/healthcheck`` endpoint for liveness probes and a ``/``
redirect to the interactive API documentation.
"""

from fastapi import APIRouter
from starlette.responses import RedirectResponse, Response

root_router = APIRouter()


@root_router.get("/healthcheck", tags=["Health"], summary="Health check")
async def healthcheck() -> Response:
    """Return a simple OK response to confirm the service is running."""
    return Response("OK")


@root_router.get("/", include_in_schema=False)
async def root():
    """Redirect the root path to the auto-generated API documentation."""
    return RedirectResponse("/docs")
