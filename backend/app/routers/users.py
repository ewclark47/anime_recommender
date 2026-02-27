from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, HTTPException

from backend.app.db import db_cursor
from backend.app.schemas import FavoriteItem, FavoriteRequest, FavoritesResponse

router = APIRouter(prefix="/users", tags=["users"])

ANIMES_DF: pd.DataFrame | None = None


def _pick_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    return None


def _title_lookup() -> dict[int, dict]:
    if ANIMES_DF is None:
        return {}
    id_col = _pick_col(ANIMES_DF, ["animeID", "id", "anime_id"])
    title_col = _pick_col(ANIMES_DF, ["title", "name"])
    image_col = _pick_col(ANIMES_DF, ["image_url", "imageUrl"])
    if id_col is None or title_col is None:
        return {}

    lookup: dict[int, dict] = {}
    for _, row in ANIMES_DF.iterrows():
        try:
            anime_id = int(row[id_col])
        except (TypeError, ValueError):
            continue
        image_url = None
        if image_col is not None:
            raw_image = row[image_col]
            if pd.notna(raw_image):
                image_url = str(raw_image)
        lookup[anime_id] = {"title": str(row[title_col]), "image_url": image_url}
    return lookup


def _ensure_user_exists(user_id: int) -> None:
    with db_cursor() as (_, cur):
        row = cur.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")


@router.get("/{user_id}/favorites", response_model=FavoritesResponse)
def list_favorites(user_id: int) -> FavoritesResponse:
    _ensure_user_exists(user_id)
    with db_cursor() as (_, cur):
        rows = cur.execute(
            "SELECT anime_id FROM favorites WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()

    lookup = _title_lookup()
    favorites = [
        FavoriteItem(
            anime_id=int(row["anime_id"]),
            title=lookup.get(int(row["anime_id"]), {}).get("title", f"Anime #{int(row['anime_id'])}"),
            image_url=lookup.get(int(row["anime_id"]), {}).get("image_url"),
        )
        for row in rows
    ]
    return FavoritesResponse(user_id=user_id, favorites=favorites)


@router.post("/{user_id}/favorites", response_model=FavoritesResponse)
def add_favorite(user_id: int, payload: FavoriteRequest) -> FavoritesResponse:
    _ensure_user_exists(user_id)
    anime_id = payload.anime_id
    with db_cursor() as (_, cur):
        cur.execute(
            "INSERT OR IGNORE INTO favorites (user_id, anime_id) VALUES (?, ?)",
            (user_id, anime_id),
        )
    return list_favorites(user_id=user_id)


@router.delete("/{user_id}/favorites/{anime_id}", response_model=FavoritesResponse)
def remove_favorite(user_id: int, anime_id: int) -> FavoritesResponse:
    _ensure_user_exists(user_id)
    with db_cursor() as (_, cur):
        cur.execute(
            "DELETE FROM favorites WHERE user_id = ? AND anime_id = ?",
            (user_id, anime_id),
        )
    return list_favorites(user_id=user_id)
