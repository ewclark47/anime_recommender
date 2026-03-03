from __future__ import annotations

import html
import json
import re
import ssl
import urllib.parse
import urllib.request
from typing import Any

import pandas as pd

from backend.app.db import db_cursor

# TODO: Add caching to avoid hitting external APIs repeatedly for the same titles, especially since MAL/Jikan can be slow and rate-limited.
# TODO: Add a background task to validate and refresh cached summaries periodically, since anime information can change and new summaries may become available.
def _normalize_title(value: str) -> str:
    cleaned = value.lower()
    cleaned = re.sub(r"[^a-z0-9\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _clean_summary(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned or None


def _strip_html(raw: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", raw)
    return _clean_summary(html.unescape(without_tags)) or ""


class AnimeSummaryService:
    def __init__(self, animes: pd.DataFrame | None):
        self.animes = animes
        self.id_col = None
        self.title_col = None
        self.mal_url_col = None
        if animes is not None:
            self.id_col = self._pick_column(["animeID", "id", "anime_id"])
            self.title_col = self._pick_column(["title", "name"])
            self.mal_url_col = self._pick_column(["mal_url", "url"])

    def _pick_column(self, candidates: list[str]) -> str | None:
        if self.animes is None:
            return None
        for col in candidates:
            if col in self.animes.columns:
                return col
        return None

    def _extract_mal_id(self, url: str | None) -> int | None:
        """Extract MAL ID from a MyAnimeList URL like 'https://myanimelist.net/anime/431'"""
        if url is None or not isinstance(url, str):
            return None
        # Match patterns like /anime/12345 or /anime/12345/title
        match = re.search(r'/anime/(\d+)', url)
        if match:
            try:
                return int(match.group(1))
            except (TypeError, ValueError):
                return None
        return None

    def _resolve_row(self, title: str | None, anime_id: int | None) -> pd.Series | None:
        if self.animes is None or self.animes.empty:
            return None

        if anime_id is not None and self.id_col is not None:
            row_by_id = self.animes.loc[pd.to_numeric(self.animes[self.id_col], errors="coerce") == anime_id]
            if not row_by_id.empty:
                return row_by_id.iloc[0]

        if title is None or self.title_col is None:
            return None

        title_series = self.animes[self.title_col].astype(str)
        exact = self.animes.loc[title_series.str.lower() == title.lower()]
        if not exact.empty:
            return exact.iloc[0]

        target_norm = _normalize_title(title)
        normalized = title_series.map(_normalize_title)
        norm_exact = self.animes.loc[normalized == target_norm]
        if not norm_exact.empty:
            return norm_exact.iloc[0]

        contains = self.animes.loc[normalized.str.contains(target_norm, na=False)]
        if not contains.empty:
            return contains.iloc[0]
        return None

    def _to_record(self, row: pd.Series | None, fallback_title: str | None, fallback_id: int | None) -> tuple[str, int | None, int | None]:
        """
        Returns (title, local_id, mal_id)
        """
        if row is None:
            title = (fallback_title or "").strip()
            if not title:
                title = f"Anime #{fallback_id}" if fallback_id is not None else "Unknown Anime"
            return title, fallback_id, None

        title = fallback_title
        if self.title_col is not None:
            raw_title = row.get(self.title_col)
            if pd.notna(raw_title):
                title = str(raw_title)
        title = (title or "").strip() or "Unknown Anime"

        resolved_id = fallback_id
        if self.id_col is not None:
            raw_id = row.get(self.id_col)
            if pd.notna(raw_id):
                try:
                    resolved_id = int(raw_id)
                except (TypeError, ValueError):
                    pass
        
        # Extract MAL ID from mal_url column
        mal_id = None
        if self.mal_url_col is not None:
            raw_url = row.get(self.mal_url_col)
            if pd.notna(raw_url):
                mal_id = self._extract_mal_id(str(raw_url))
        
        return title, resolved_id, mal_id

    def _http_json(self, url: str, timeout: float = 2.5) -> dict[str, Any] | None:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "anime-recommender/1.0",
                "Accept": "application/json",
            },
        )
        try:
            # Create SSL context that doesn't verify certificates (for development)
            # In production, you should use ssl.create_default_context()
            ssl_context = ssl._create_unverified_context()
            with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception:
            return None

    def _http_text(self, url: str, timeout: float = 2.5) -> str | None:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "anime-recommender/1.0",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        try:
            # Create SSL context that doesn't verify certificates (for development)
            # In production, you should use ssl.create_default_context()
            ssl_context = ssl._create_unverified_context()
            with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as response:
                return response.read().decode("utf-8", errors="ignore")
        except Exception:
            return None

    def _match_titles(self, entry: dict[str, Any], target_norm: str) -> bool:
        titles_to_match: list[str] = []
        for key in ("title", "title_english", "title_japanese"):
            raw = entry.get(key)
            if isinstance(raw, str) and raw.strip():
                titles_to_match.append(raw)
        raw_titles = entry.get("titles")
        if isinstance(raw_titles, list):
            for item in raw_titles:
                if isinstance(item, dict):
                    raw = item.get("title")
                    if isinstance(raw, str) and raw.strip():
                        titles_to_match.append(raw)
        return any(_normalize_title(candidate) == target_norm for candidate in titles_to_match)

    def _fetch_jikan_entry(self, title: str) -> dict[str, Any] | None:
        endpoint = "https://api.jikan.moe/v4/anime"
        query = urllib.parse.urlencode({"q": title, "limit": 5})
        payload = self._http_json(f"{endpoint}?{query}")
        if payload is None:
            return None

        rows = payload.get("data")
        if not isinstance(rows, list):
            return None
        if not rows:
            return None

        target_norm = _normalize_title(title)
        for entry in rows:
            if isinstance(entry, dict) and self._match_titles(entry, target_norm):
                return entry
        for entry in rows:
            if isinstance(entry, dict):
                return entry
        return None

    def _fetch_jikan_entry_by_id(self, anime_id: int | None) -> dict[str, Any] | None:
        if anime_id is None:
            return None
        payload = self._http_json(f"https://api.jikan.moe/v4/anime/{anime_id}")
        if payload is None:
            return None
        entry = payload.get("data")
        if isinstance(entry, dict):
            return entry
        return None

    def _fetch_summary_from_mal_jikan(self, jikan_entry: dict[str, Any] | None) -> str | None:
        if not isinstance(jikan_entry, dict):
            return None
        synopsis = _clean_summary(jikan_entry.get("synopsis"))
        if synopsis:
            return synopsis
        return _clean_summary(jikan_entry.get("background"))

    def _fetch_summary_from_mal_page(self, jikan_entry: dict[str, Any] | None) -> str | None:
        if not isinstance(jikan_entry, dict):
            return None

        url = jikan_entry.get("url")
        if not isinstance(url, str) or "myanimelist.net/anime/" not in url:
            return None

        html_doc = self._http_text(url)
        if not html_doc:
            return None

        match = re.search(
            r"<p[^>]*itemprop=[\"']description[\"'][^>]*>(.*?)</p>",
            html_doc,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if match:
            return _clean_summary(_strip_html(match.group(1)))

        json_ld_match = re.search(
            r'"description"\s*:\s*"([^"]+)"',
            html_doc,
            flags=re.IGNORECASE,
        )
        if json_ld_match:
            raw = json_ld_match.group(1).replace("\\n", " ")
            return _clean_summary(html.unescape(raw))
        return None

    def _fetch_summary_from_wikipedia(self, title: str) -> str | None:
        def fetch_page_summary(page_title: str) -> str | None:
            encoded = urllib.parse.quote(page_title, safe="")
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}"
            payload = self._http_json(url)
            if payload is None:
                return None
            text = payload.get("extract")
            if isinstance(text, str):
                return _clean_summary(text)
            return None

        direct = fetch_page_summary(title)
        if direct:
            return direct

        search_url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
            {
                "action": "query",
                "list": "search",
                "srsearch": f"{title} anime",
                "format": "json",
                "utf8": 1,
                "srlimit": 1,
            }
        )
        search_payload = self._http_json(search_url)
        if search_payload is None:
            return None

        items = search_payload.get("query", {}).get("search", [])
        if not isinstance(items, list) or not items:
            return None
        first = items[0]
        if not isinstance(first, dict):
            return None
        matched_title = first.get("title")
        if not isinstance(matched_title, str) or not matched_title.strip():
            return None
        return fetch_page_summary(matched_title)

    def _cache_get(self, title_norm: str, anime_id: int | None) -> dict[str, Any] | None:
        with db_cursor() as (_, cur):
            row = None
            if anime_id is not None:
                row = cur.execute(
                    """
                    SELECT anime_id, title, summary, source
                    FROM anime_summaries
                    WHERE anime_id = ?
                    LIMIT 1
                    """,
                    (anime_id,),
                ).fetchone()
            if row is None:
                row = cur.execute(
                    """
                    SELECT anime_id, title, summary, source
                    FROM anime_summaries
                    WHERE title_norm = ?
                    LIMIT 1
                    """,
                    (title_norm,),
                ).fetchone()

        if row is None:
            return None
        source = str(row["source"])
        if source == "generated":
            return None
        if source == "jikan":
            source = "mal"
        return {
            "anime_id": int(row["anime_id"]) if row["anime_id"] is not None else None,
            "title": str(row["title"]),
            "summary": str(row["summary"]),
            "source": source,
        }

    def _cache_set(self, title_norm: str, title: str, anime_id: int | None, summary: str, source: str) -> None:
        with db_cursor() as (_, cur):
            cur.execute(
                """
                INSERT INTO anime_summaries (title_norm, title, anime_id, summary, source, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(title_norm) DO UPDATE SET
                    title = excluded.title,
                    anime_id = excluded.anime_id,
                    summary = excluded.summary,
                    source = excluded.source,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (title_norm, title, anime_id, summary, source),
            )

    def get_summary(self, title: str | None = None, anime_id: int | None = None) -> dict[str, Any]:
        row = self._resolve_row(title=title, anime_id=anime_id)
        canonical_title, canonical_id, mal_id = self._to_record(row=row, fallback_title=title, fallback_id=anime_id)
        title_norm = _normalize_title(canonical_title)

        cached = self._cache_get(title_norm=title_norm, anime_id=canonical_id)
        if cached is not None:
            return cached

        summary = None
        source = ""

        # Use MAL ID if available, otherwise fall back to canonical_id
        jikan_id = mal_id if mal_id is not None else canonical_id
        jikan_entry = self._fetch_jikan_entry_by_id(jikan_id)
        if not jikan_entry:
            jikan_entry = self._fetch_jikan_entry(canonical_title)
        summary = self._fetch_summary_from_mal_jikan(jikan_entry)
        if summary:
            source = "mal"
        else:
            summary = self._fetch_summary_from_mal_page(jikan_entry)
            if summary:
                source = "mal"
            else:
                summary = self._fetch_summary_from_wikipedia(canonical_title)
                if summary:
                    source = "wikipedia"

        if not summary:
            summary = (
                f"Summary currently unavailable for {canonical_title}. "
                "Could not retrieve a synopsis from MyAnimeList or Wikipedia."
            )
            source = "unavailable"

        self._cache_set(
            title_norm=title_norm,
            title=canonical_title,
            anime_id=canonical_id,
            summary=summary,
            source=source,
        )
        return {
            "anime_id": canonical_id,
            "title": canonical_title,
            "summary": summary,
            "source": source,
        }
