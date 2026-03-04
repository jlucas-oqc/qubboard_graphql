from fastapi import APIRouter
from starlette.responses import RedirectResponse

root_router = APIRouter()


@root_router.get("/")
async def root():
    return RedirectResponse("/docs")
