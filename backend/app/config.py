from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    data_dir: str = "./"  # relative to repo root
    animes_csv: str = "animes.csv"
    ratings_csv: str = "ratings.csv"
    sqlite_path: str = "backend/app/app.db"
    recommender_model_path: str = "pretrained_bert.pth"  # placeholder
    debug: bool = True
    allow_origins: list[str] = ["*"]

    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache
def get_settings() -> Settings:
    return Settings()
