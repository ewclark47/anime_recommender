import os
from functools import lru_cache

from pydantic_settings import BaseSettings


def _default_sqlite_path() -> str:
    # Vercel's filesystem is read-only except /tmp.
    if os.getenv("VERCEL"):
        return "/tmp/app.db"
    return "backend/app/app.db"

class Settings(BaseSettings):
    data_dir: str = "./"  # relative to repo root
    animes_csv: str = "animes.csv"
    ratings_csv: str = "ratings.csv"
    sqlite_path: str = _default_sqlite_path()
    recommender_model_path: str = "pretrained_bert.pth"  # placeholder
    debug: bool = True
    allow_origins: list[str] = ["*"]

    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache
def get_settings() -> Settings:
    return Settings()
