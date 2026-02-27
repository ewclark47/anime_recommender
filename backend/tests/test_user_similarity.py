import importlib
import uuid

from fastapi.testclient import TestClient


def get_app():
    module = importlib.import_module("backend.main")
    return module.app


def unique_username(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def register_user(client: TestClient, username: str, password: str = "testpass123") -> int:
    resp = client.post("/auth/register", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return int(resp.json()["user"]["id"])


def test_user_similarity_recommendations_flow():
    app = get_app()
    with TestClient(app) as client:
        user_a = register_user(client, unique_username("alice"))
        user_b = register_user(client, unique_username("bob"))

        anime_resp = client.get("/anime", params={"limit": 5})
        assert anime_resp.status_code == 200
        anime_rows = anime_resp.json()
        assert len(anime_rows) >= 3

        anime_1 = int(anime_rows[0]["id"])
        anime_2 = int(anime_rows[1]["id"])
        anime_3 = int(anime_rows[2]["id"])

        resp = client.post(f"/users/{user_a}/favorites", json={"anime_id": anime_1})
        assert resp.status_code == 200
        resp = client.post(f"/users/{user_a}/favorites", json={"anime_id": anime_2})
        assert resp.status_code == 200

        resp = client.post(f"/users/{user_b}/favorites", json={"anime_id": anime_2})
        assert resp.status_code == 200
        resp = client.post(f"/users/{user_b}/favorites", json={"anime_id": anime_3})
        assert resp.status_code == 200

        recommend_resp = client.get(f"/recommend/user/{user_a}", params={"limit": 5})
        assert recommend_resp.status_code == 200, recommend_resp.text
        payload = recommend_resp.json()
        returned_ids = [int(item["anime_id"]) for item in payload["recommendations"]]
        assert anime_3 in returned_ids
