from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    redis_url: str = "redis://localhost:6379"
    langgraph_db_url: str

    class Config:
        env_file = ".env"

settings = Settings()
