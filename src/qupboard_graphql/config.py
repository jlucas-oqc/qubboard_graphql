from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GRAPHQL_PATH: str = "/graphql"
    REST_PATH: str = "/rest"
    DATABASE_URL: str = "sqlite:///./qupboard.db"


settings = Settings()
