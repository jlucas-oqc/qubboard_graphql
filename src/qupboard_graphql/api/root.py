from fastapi import APIRouter
from starlette.responses import RedirectResponse

from qupboard_graphql.config import settings

root_router = APIRouter()


@root_router.get("/")
async def root():
    return RedirectResponse(settings.GRAPHQL_PATH)
