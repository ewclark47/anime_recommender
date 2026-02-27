import importlib

from fastapi.testclient import TestClient


def get_app():
    module = importlib.import_module("backend.main")
    return module.app


def test_anime_summary_endpoint_returns_summary():
    app = get_app()
    with TestClient(app) as client:
        anime_resp = client.get("/anime", params={"limit": 1})
        assert anime_resp.status_code == 200, anime_resp.text
        rows = anime_resp.json()
        assert rows, "Expected at least one anime row in dataset"

        first_title = rows[0]["name"]
        first_id = rows[0]["id"]
        summary_resp = client.get(
            "/anime/summary",
            params={"title": first_title, "anime_id": first_id},
        )
        assert summary_resp.status_code == 200, summary_resp.text
        payload = summary_resp.json()
        assert payload["title"]
        assert payload["summary"]
        assert isinstance(payload["summary"], str)
        assert payload["source"] in {"mal", "wikipedia", "unavailable"}
