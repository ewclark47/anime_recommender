# Anime Recommender - Local Development

This project has:
- `backend/`: FastAPI API server
- `frontend/`: static web UI

## Prerequisites

- Python 3.11+ (project currently uses a local `.venv`)
- Dependencies installed in `.venv`

If needed:

```bash
python3 -m venv .venv
./.venv/bin/pip install -r backend/requirements.txt
```

## Start Dev Servers

From the repository root:

1. Start backend (FastAPI on port `8000`):

```bash
./.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

2. Start frontend (static server on port `5500`):

```bash
python3 -m http.server 5500 --directory frontend --bind 127.0.0.1
```

3. Open the app:

- Frontend: `http://127.0.0.1:5500`
- Backend health: `http://127.0.0.1:8000/health`

## Optional: Run in Background

```bash
nohup ./.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000 >/tmp/anime-backend.log 2>&1 &
nohup python3 -m http.server 5500 --directory frontend --bind 127.0.0.1 >/tmp/anime-frontend.log 2>&1 &
```

Logs:

- `/tmp/anime-backend.log`
- `/tmp/anime-frontend.log`

## Stop Servers

If running in foreground, press `Ctrl+C` in each terminal.

If running in background:

```bash
pkill -f "uvicorn backend.main:app"
pkill -f "http.server 5500 --directory frontend"
```
