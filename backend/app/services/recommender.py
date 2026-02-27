from __future__ import annotations

import re
from typing import Any

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel


def _normalize_title(value: str) -> str:
    cleaned = value.lower()
    cleaned = re.sub(r"[^a-z0-9\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned

class TitleSimilarityRecommender:
    """
    TF-IDF cosine-similarity recommender aligned with EDA.ipynb workflow.
    Uses combined text features:
    - genres_detailed
    - type
    - year
    - score
    """

    def __init__(self, animes: pd.DataFrame | None):
        self.animes = animes.copy() if animes is not None else None
        self.title_col: str | None = None
        self.id_col: str | None = None
        self.image_col: str | None = None
        self.vectorizer: TfidfVectorizer | None = None
        self.tfidf_matrix = None
        self._build()

    def _build(self) -> None:
        if self.animes is None or self.animes.empty:
            return

        self.title_col = self._pick_column(["title", "name"])
        self.id_col = self._pick_column(["animeID", "id", "anime_id"])
        self.image_col = self._pick_column(["image_url", "imageUrl"])
        if self.title_col is None:
            return

        df = self.animes.copy()
        df = df.dropna(subset=[self.title_col])
        df[self.title_col] = df[self.title_col].astype(str).str.strip()
        df = df[df[self.title_col] != ""]
        if df.empty:
            return
        self.animes = df.reset_index(drop=True)

        combined_features = self._build_combined_features(self.animes)
        self.vectorizer = TfidfVectorizer()
        self.tfidf_matrix = self.vectorizer.fit_transform(combined_features)

    def _pick_column(self, candidates: list[str]) -> str | None:
        if self.animes is None:
            return None
        for col in candidates:
            if col in self.animes.columns:
                return col
        return None

    def _build_combined_features(self, df: pd.DataFrame) -> pd.Series:
        # Mirror notebook behavior when possible, with a fallback to 'genres'.
        if "genres_detailed" in df.columns:
            genres_stringified = (
                df["genres_detailed"]
                .fillna("")
                .astype(str)
                .str.replace(",", "", regex=False)
                .str.replace("[", "", regex=False)
                .str.replace("]", "", regex=False)
                .str.replace("'", "", regex=False)
            )
            type_part = df["type"].fillna("").astype(str) if "type" in df.columns else ""
            year_part = df["year"].fillna("").astype(str) if "year" in df.columns else ""
            score_part = df["score"].fillna("").astype(str) if "score" in df.columns else ""
            return (
                genres_stringified
                + " "
                + type_part
                + " "
                + year_part
                + " "
                + score_part
            ).fillna("")

        genres_fallback = df["genres"].fillna("").astype(str) if "genres" in df.columns else ""
        return genres_fallback.str.replace("|", " ", regex=False).fillna("")

    @property
    def ready(self) -> bool:
        return (
            self.animes is not None
            and self.title_col is not None
            and self.vectorizer is not None
            and self.tfidf_matrix is not None
        )

    def _resolve_title_index(self, title: str) -> int | None:
        if not self.ready:
            return None
        assert self.animes is not None
        assert self.title_col is not None

        exact_mask = self.animes[self.title_col] == title
        if exact_mask.any():
            return int(exact_mask[exact_mask].index[0])

        target_norm = _normalize_title(title)
        norm_series = self.animes[self.title_col].map(_normalize_title)

        norm_exact_mask = norm_series == target_norm
        if norm_exact_mask.any():
            return int(norm_exact_mask[norm_exact_mask].index[0])

        contains_mask = norm_series.str.contains(target_norm, na=False)
        if contains_mask.any():
            return int(contains_mask[contains_mask].index[0])

        return None

    def recommend_by_title(self, title: str, limit: int = 10, offset: int = 0) -> list[dict[str, Any]]:
        if not self.ready:
            raise RuntimeError("Recommender not initialized")

        index = self._resolve_title_index(title)
        if index is None:
            raise KeyError(f"Anime title not found: {title}")

        assert self.animes is not None
        assert self.title_col is not None
        assert self.tfidf_matrix is not None

        query_title = str(self.animes.iloc[index][self.title_col])
        query_norm = _normalize_title(query_title)
        similarity_scores = linear_kernel(self.tfidf_matrix[index], self.tfidf_matrix).flatten()
        sorted_indexes = similarity_scores.argsort()[::-1]

        results: list[dict[str, Any]] = []
        for candidate_index in sorted_indexes:
            if candidate_index == index:
                continue

            candidate_title = str(self.animes.iloc[candidate_index][self.title_col]).strip()
            if not candidate_title:
                continue
            if query_norm and query_norm in _normalize_title(candidate_title):
                continue

            item: dict[str, Any] = {"title": candidate_title}

            if self.id_col is not None:
                raw_id = self.animes.iloc[candidate_index][self.id_col]
                if pd.notna(raw_id):
                    try:
                        item["anime_id"] = int(raw_id)
                    except (TypeError, ValueError):
                        item["anime_id"] = None
            if self.image_col is not None:
                raw_image = self.animes.iloc[candidate_index][self.image_col]
                if pd.notna(raw_image):
                    item["image_url"] = str(raw_image)

            results.append(item)

        return results[offset : offset + limit]
