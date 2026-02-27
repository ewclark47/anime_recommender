from fastapi import APIRouter, HTTPException
from typing import List
import pandas as pd

from backend.app.schemas import Anime, AnimeSummaryResponse
from backend.app.services.summaries import AnimeSummaryService

router = APIRouter(prefix="/anime", tags=["anime"])

# In-memory references set by lifespan
ANIMES_DF: pd.DataFrame | None = None
SUMMARY_SERVICE: AnimeSummaryService | None = None


def _pick_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    return None


def _to_anime(row: pd.Series, id_col: str | None, name_col: str | None) -> Anime:
    raw_id = row[id_col] if id_col is not None else row.name
    try:
        anime_id = int(raw_id)
    except (TypeError, ValueError):
        anime_id = int(row.name)

    raw_name = row[name_col] if name_col is not None else None
    anime_name = str(raw_name) if raw_name is not None else ""

    image_url = row.get("image_url", row.get("imageUrl"))
    if pd.isna(image_url):
        image_url = None

    return Anime(
        id=anime_id,
        name=anime_name,
        genre=row.get("genre", row.get("genres")),
        episodes=row.get("episodes"),
        type=row.get("type"),
        rating=row.get("rating", row.get("score")),
        members=row.get("members"),
        image_url=str(image_url) if image_url is not None else None,
    )


@router.get("/", response_model=List[Anime])
def list_anime(limit: int = 50, skip: int = 0) -> List[Anime]:
    if ANIMES_DF is None:
        return []
    id_col = _pick_col(ANIMES_DF, ["id", "animeID", "anime_id"])
    name_col = _pick_col(ANIMES_DF, ["name", "title"])
    subset = ANIMES_DF.iloc[skip: skip + limit]
    return [_to_anime(row=row, id_col=id_col, name_col=name_col) for _, row in subset.iterrows()]

@router.get("/top", response_model=List[Anime])
def top_rated(limit: int = 10) -> List[Anime]:
    if ANIMES_DF is None:
        return []
    id_col = _pick_col(ANIMES_DF, ["id", "animeID", "anime_id"])
    name_col = _pick_col(ANIMES_DF, ["name", "title"])
    rating_col = _pick_col(ANIMES_DF, ["rating", "score"])
    if name_col is None:
        return []

    if rating_col is None:
        subset = ANIMES_DF.iloc[:limit]
    else:
        subset = ANIMES_DF.copy()
        subset[rating_col] = pd.to_numeric(subset[rating_col], errors="coerce")
        subset = subset.dropna(subset=[rating_col]).sort_values(by=rating_col, ascending=False).iloc[:limit]

    return [_to_anime(row=row, id_col=id_col, name_col=name_col) for _, row in subset.iterrows()]

@router.get("/search", response_model=List[Anime])
def search(q: str, limit: int = 20) -> List[Anime]:
    if ANIMES_DF is None:
        return []
    id_col = _pick_col(ANIMES_DF, ["id", "animeID", "anime_id"])
    name_col = _pick_col(ANIMES_DF, ["name", "title"])
    if name_col is None:
        return []
    mask = ANIMES_DF[name_col].astype(str).str.contains(q, case=False, na=False)
    subset = ANIMES_DF[mask].iloc[:limit]
    return [_to_anime(row=row, id_col=id_col, name_col=name_col) for _, row in subset.iterrows()]

@router.get("/summary", response_model=AnimeSummaryResponse)
def get_anime_summary(title: str, anime_id: int | None = None) -> AnimeSummaryResponse:
    if SUMMARY_SERVICE is None:
        raise HTTPException(status_code=503, detail="Summary service not ready")
    summary = SUMMARY_SERVICE.get_summary(title=title, anime_id=anime_id)
    return AnimeSummaryResponse(**summary)


@router.get("/{anime_id}", response_model=Anime)
def get_anime(anime_id: int) -> Anime:
    if ANIMES_DF is None:
        raise HTTPException(status_code=404, detail="Anime dataset not loaded")
    id_col = _pick_col(ANIMES_DF, ["id", "animeID", "anime_id"])
    name_col = _pick_col(ANIMES_DF, ["name", "title"])
    if id_col is None:
        raise HTTPException(status_code=500, detail="Anime ID column not found")
    row = ANIMES_DF.loc[ANIMES_DF[id_col] == anime_id]
    if row.empty:
        raise HTTPException(status_code=404, detail="Anime not found")
    r = row.iloc[0]
    return _to_anime(row=r, id_col=id_col, name_col=name_col)
