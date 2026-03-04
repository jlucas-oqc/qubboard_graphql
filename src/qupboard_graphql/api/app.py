from contextlib import asynccontextmanager

from fastapi import FastAPI

# from qupboard_graphql.api.graphql import graphql_router
from qupboard_graphql.api.graphql import graphql_router
from qupboard_graphql.api.rest import rest_router
from qupboard_graphql.api.root import root_router
from qupboard_graphql.config import settings
from qupboard_graphql.db.database import Base
from qupboard_graphql.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


def get_app():
    app = FastAPI(lifespan=lifespan)
    app.include_router(root_router, prefix="")
    app.include_router(rest_router, prefix=settings.REST_PATH)
    app.include_router(graphql_router, prefix=settings.GRAPHQL_PATH)
    return app
