from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "password"
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_DB: str = "news_db"

    NEWS_API_KEY: str = ""
    # Comma-separated query terms used for /v2/everything rotation.
    NEWS_QUERY_TERMS: str = "bitcoin,technology,finance,ai,startups"

    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"

    @property
    def QUERY_TERMS(self) -> list[str]:
        terms = [
            term.strip() for term in self.NEWS_QUERY_TERMS.split(",") if term.strip()
        ]
        return terms or ["bitcoin"]

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache()
def get_settings():
    return Settings()
