from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.app.db import db_cursor
from backend.app.schemas import AuthRequest, AuthResponse, UserResponse
from backend.app.services.auth import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
def register(payload: AuthRequest) -> AuthResponse:
    username = payload.username.strip()
    if not username or not payload.password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    with db_cursor() as (_, cur):
        existing = cur.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Username already exists")

        cur.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, hash_password(payload.password)),
        )
        user_id = int(cur.lastrowid)

    return AuthResponse(user=UserResponse(id=user_id, username=username))


@router.post("/login", response_model=AuthResponse)
def login(payload: AuthRequest) -> AuthResponse:
    username = payload.username.strip()
    if not username or not payload.password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    with db_cursor() as (_, cur):
        row = cur.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()

    if row is None or not verify_password(payload.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return AuthResponse(user=UserResponse(id=int(row["id"]), username=str(row["username"])))
