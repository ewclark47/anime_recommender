import importlib
from fastapi.testclient import TestClient

def get_app():
    module = importlib.import_module('backend.main')
    return module.app

def test_health():
    app = get_app()
    client = TestClient(app)
    resp = client.get('/health')
    assert resp.status_code == 200
    assert resp.json()['status'] == 'ok'
