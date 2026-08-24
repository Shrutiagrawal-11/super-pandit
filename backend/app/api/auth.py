"""Email/password auth, structured so Google/Apple/phone-OTP can be added
as more `provider` rows in auth_identities without changing this shape:
a user always has one row in `users`, one or more rows in `auth_identities`
(one per sign-in method they've linked).
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

import bcrypt
import jwt
import psycopg
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, EmailStr, Field

from core.config import DATABASE_URL, JWT_SECRET

router = APIRouter()
JWT_ALGORITHM = "HS256"
TOKEN_TTL = timedelta(days=30)


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    token: str
    user_id: int
    display_name: str | None = None


def _issue_token(user_id):
    payload = {"user_id": user_id, "exp": datetime.now(timezone.utc) + TOKEN_TTL}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def current_user_id(authorization: str | None = Header(default=None)):
    """Dependency for routes that require a signed-in user. Raises 401 if
    the token is missing or invalid; guest-usable routes don't depend on this.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header")
    token = authorization.removeprefix("Bearer ")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token")
    return payload["user_id"]


@router.post("/auth/signup", response_model=AuthResponse)
def signup(req: SignupRequest):
    password_hash = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()

    conn = psycopg.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE email = %s", (req.email,))
    if cur.fetchone():
        cur.close()
        conn.close()
        raise HTTPException(409, "An account with this email already exists")

    cur.execute(
        "INSERT INTO users (email, password_hash, display_name) VALUES (%s, %s, %s) RETURNING id",
        (req.email, password_hash, req.display_name),
    )
    user_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO auth_identities (user_id, provider, provider_uid) VALUES (%s, 'email', %s)",
        (user_id, req.email),
    )
    conn.commit()
    cur.close()
    conn.close()

    return AuthResponse(token=_issue_token(user_id), user_id=user_id, display_name=req.display_name)


@router.post("/auth/login", response_model=AuthResponse)
def login(req: LoginRequest):
    conn = psycopg.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT id, password_hash, display_name FROM users WHERE email = %s", (req.email,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row or not row[1] or not bcrypt.checkpw(req.password.encode(), row[1].encode()):
        raise HTTPException(401, "Incorrect email or password")

    user_id, _, display_name = row
    return AuthResponse(token=_issue_token(user_id), user_id=user_id, display_name=display_name)
