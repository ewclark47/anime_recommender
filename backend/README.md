# Anime FastAPI Backend

## Features
- Health check (`/health`)
- List anime (`/anime` with pagination)
- Get anime by id (`/anime/{id}`)
- Search anime by name (`/anime/search?q=Naruto`)
- Get title-based recommendations (`/recommend?title=Death+Note&limit=10`)
- Register/login users (`/auth/register`, `/auth/login`)
- Add/remove/list favorites (`/users/{user_id}/favorites`)
- Get user-similarity recommendations (`/recommend/user/{user_id}?limit=10`)

## Setup

Create virtual environment (optional):

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r backend/requirements.txt
```

Run server:

```bash
uvicorn backend.main:app --reload
```

## Environment Variables
Create `.env` in repo root if needed:
```
DATA_DIR=./
```
(Defaults already point to CSV files at the repo root.)

## Tests

Install dev dependency `pytest` if not already:
```bash
pip install pytest
```
Run tests:
```bash
pytest -q
```

## Recommendation behavior
- The recommender follows the `EDA.ipynb` cosine-similarity approach (TF-IDF + cosine).
- It builds text features from: `genres_detailed`, `type`, `year`, and `score`.
- If `genres_detailed` is unavailable, it falls back to `genres`.
- User-similarity recommendations are collaborative filtering based on user favorites,
  using Jaccard similarity between users.
