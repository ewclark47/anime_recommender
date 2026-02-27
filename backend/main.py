from __future__ import annotations
from fastapi import FastAPI
from contextlib import asynccontextmanager
import pandas as pd
from fastapi.middleware.cors import CORSMiddleware

# Use package-qualified imports so "from backend.main import app" works.
from backend.app.config import get_settings
from backend.app.db import init_db
from backend.app.routers import auth as auth_router
from backend.app.routers import anime as anime_router
from backend.app.routers import recommend as recommend_router
from backend.app.routers import users as users_router
from backend.app.services.recommender import TitleSimilarityRecommender
from backend.app.services.summaries import AnimeSummaryService
from backend.app.services.user_similarity import UserSimilarityRecommender

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    init_db()
    # Load anime dataset used by list/search endpoints and recommender.
    try:
        animes = pd.read_csv(settings.data_dir + settings.animes_csv)
    except Exception:
        animes = None

    anime_router.ANIMES_DF = animes
    anime_router.SUMMARY_SERVICE = AnimeSummaryService(animes=animes)
    users_router.ANIMES_DF = animes
    recommend_router.RECOMMENDER = TitleSimilarityRecommender(animes=animes)
    recommend_router.USER_RECOMMENDER = UserSimilarityRecommender(animes=animes)
    yield
    # Cleanup if needed
    anime_router.ANIMES_DF = None
    anime_router.SUMMARY_SERVICE = None
    users_router.ANIMES_DF = None
    recommend_router.RECOMMENDER = None
    recommend_router.USER_RECOMMENDER = None

app = FastAPI(title="Anime Recommender API", lifespan=lifespan)
settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(anime_router.router)
app.include_router(recommend_router.router)
app.include_router(auth_router.router)
app.include_router(users_router.router)

# For local dev: uvicorn backend.main:app --reload
