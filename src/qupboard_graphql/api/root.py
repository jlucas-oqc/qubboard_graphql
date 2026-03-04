from fastapi import APIRouter
from starlette.responses import RedirectResponse, Response

root_router = APIRouter()


@root_router.get("/healthcheck", tags=["Health"], summary="Health check")
async def healthcheck() -> Response:
    """Return a simple OK response to confirm the service is running."""
    return Response("OK")


@root_router.get("/")
async def root():
    return RedirectResponse("/docs")
