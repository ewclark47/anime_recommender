from __future__ import annotations

from collections import defaultdict

import pandas as pd

from backend.app.db import db_cursor


class UserSimilarityRecommender:
    def __init__(self, animes: pd.DataFrame | None):
        self.animes = animes
        self.id_col = None
        self.title_col = None
        self.image_col = None
        if animes is not None:
            self.id_col = self._pick_column(["animeID", "id", "anime_id"])
            self.title_col = self._pick_column(["title", "name"])
            self.image_col = self._pick_column(["image_url", "imageUrl"])

    def _pick_column(self, candidates: list[str]) -> str | None:
        if self.animes is None:
            return None
        for col in candidates:
            if col in self.animes.columns:
                return col
        return None

    def _anime_lookup(self) -> dict[int, dict]:
        if self.animes is None or self.id_col is None or self.title_col is None:
            return {}
        lookup: dict[int, dict] = {}
        for _, row in self.animes.iterrows():
            try:
                anime_id = int(row[self.id_col])
            except (TypeError, ValueError):
                continue
            image_url = None
            if self.image_col is not None:
                raw_image = row[self.image_col]
                if pd.notna(raw_image):
                    image_url = str(raw_image)
            lookup[anime_id] = {"title": str(row[self.title_col]), "image_url": image_url}
        return lookup

    def recommend_for_user(self, user_id: int, limit: int = 10, offset: int = 0) -> list[dict]:
        with db_cursor() as (_, cur):
            rows = cur.execute(
                "SELECT user_id, anime_id FROM favorites ORDER BY user_id"
            ).fetchall()

        if not rows:
            return []

        user_favorites: dict[int, set[int]] = defaultdict(set)
        for row in rows:
            user_favorites[int(row["user_id"])].add(int(row["anime_id"]))

        target = user_favorites.get(user_id, set())
        if not target:
            return []

        similarity_scores: dict[int, float] = {}
        for other_user_id, other_set in user_favorites.items():
            if other_user_id == user_id:
                continue
            union = target | other_set
            if not union:
                continue
            intersection = target & other_set
            jaccard = len(intersection) / len(union)
            if jaccard > 0:
                similarity_scores[other_user_id] = jaccard

        if not similarity_scores:
            return []

        candidate_scores: dict[int, float] = defaultdict(float)
        for other_user_id, sim in similarity_scores.items():
            for anime_id in user_favorites[other_user_id]:
                if anime_id in target:
                    continue
                candidate_scores[anime_id] += sim

        if not candidate_scores:
            return []

        lookup = self._anime_lookup()
        ranked = sorted(candidate_scores.items(), key=lambda x: x[1], reverse=True)

        recommendations: list[dict] = []
        for anime_id, score in ranked[offset : offset + limit]:
            meta = lookup.get(anime_id, {"title": f"Anime #{anime_id}", "image_url": None})
            recommendations.append(
                {
                    "anime_id": anime_id,
                    "title": meta["title"],
                    "image_url": meta.get("image_url"),
                    "score": float(score),
                }
            )
        return recommendations
