import os
import sqlite3
from pathlib import Path
from uuid import uuid4
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from pwdlib import PasswordHash

# ======================================
# 1. CONFIGURATION
# ======================================

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("AUTH_JWT_SECRET")

if not SECRET_KEY or len(SECRET_KEY) < 32:
    raise RuntimeError(
        "Configure AUTH_JWT_SECRET dans le fichier .env"
    )

ALGORITHM = "HS256"
TOKEN_DURATION_HOURS = 8

DB_PATH = BASE_DIR / "auth.db"

app = FastAPI(
    title="MSOA - Authentication Microservice",
    version="1.0.0"
)

password_hasher = PasswordHash.recommended()
bearer_scheme = HTTPBearer(auto_error=False)

# ======================================
# 2. CONFIGURATION CORS
# ======================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# ======================================
# 3. BASE DE DONNEES SQLITE
# ======================================

@contextmanager
def get_db():
    connection = sqlite3.connect(
        DB_PATH,
        timeout=10
    )
    connection.row_factory = sqlite3.Row

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_database():
    with get_db() as db:

        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'CUSTOMER'
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS revoked_tokens (
                jti TEXT PRIMARY KEY,
                expires_at INTEGER NOT NULL
            )
        """)


init_database()

# ======================================
# 4. MODELES DE DONNEES
# ======================================

class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ======================================
# 5. FONCTIONS UTILITAIRES
# ======================================

def find_user_by_email(email):
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        return dict(row) if row else None


def find_user_by_id(user_id):
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()

        return dict(row) if row else None


def safe_user(user):
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"]
    }


def create_token(user_id):
    now = datetime.now(timezone.utc)

    payload = {
        "sub": user_id,
        "jti": str(uuid4()),
        "iat": now,
        "exp": now + timedelta(
            hours=TOKEN_DURATION_HOURS
        )
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def get_current_session(
    credentials: HTTPAuthorizationCredentials = Depends(
        bearer_scheme
    )
):
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = payload["sub"]
        jti = payload["jti"]

    except (jwt.InvalidTokenError, KeyError, TypeError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    with get_db() as db:
        revoked = db.execute(
            "SELECT 1 FROM revoked_tokens WHERE jti = ?",
            (jti,)
        ).fetchone()

    if revoked:
        raise HTTPException(
            status_code=401,
            detail="Token has been revoked"
        )

    user = find_user_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    return user


# ======================================
# 6. GESTION DES ERREURS
# ======================================

@app.exception_handler(HTTPException)
async def http_error_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail}
    )


# ======================================
# 7. ENDPOINT REGISTER
# ======================================

@app.post("/api/auth/register", status_code=201)
def register(data: RegisterRequest):

    name = data.name.strip()
    email = str(data.email).strip().lower()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Name is required"
        )

    if find_user_by_email(email):
        raise HTTPException(
            status_code=409,
            detail="Email already registered"
        )

    user_id = str(uuid4())

    hashed_password = password_hasher.hash(
        data.password
    )

    try:
        with get_db() as db:
            db.execute("""
                INSERT INTO users
                (id, name, email, password_hash, role)
                VALUES (?, ?, ?, ?, ?)
            """, (
                user_id,
                name,
                email,
                hashed_password,
                "CUSTOMER"
            ))

    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Email already registered"
        )

    return {
        "id": user_id,
        "name": name,
        "email": email,
        "role": "CUSTOMER"
    }


# ======================================
# 8. ENDPOINT LOGIN
# ======================================

@app.post("/api/auth/login")
def login(data: LoginRequest):

    email = str(data.email).strip().lower()

    user = find_user_by_email(email)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    valid_password = password_hasher.verify(
        data.password,
        user["password_hash"]
    )

    if not valid_password:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    token = create_token(user["id"])

    return {
        "user": safe_user(user),
        "token": token
    }


# ======================================
# 9. ENDPOINT ME
# ======================================

@app.get("/api/auth/me")
def get_me(
    current_user=Depends(get_current_session)
):
    return safe_user(current_user)


# ======================================
# 10. ENDPOINT LOGOUT
# ======================================

@app.post("/api/auth/logout")
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(
        bearer_scheme
    )
):
    if credentials is None:
        return {"success": True}

    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

    except jwt.InvalidTokenError:
        return {"success": True}

    jti = payload.get("jti")
    expires_at = payload.get("exp")

    if jti and expires_at:
        with get_db() as db:

            db.execute(
                """INSERT OR IGNORE INTO revoked_tokens
                   (jti, expires_at) VALUES (?, ?)""",
                (jti, int(expires_at))
            )

            db.execute(
                "DELETE FROM revoked_tokens WHERE expires_at < ?",
                (int(datetime.now(timezone.utc).timestamp()),)
            )

    return {"success": True}


# ======================================
# 11. ROOT - TEST SERVEUR
# ======================================

@app.get("/")
def home():
    return {
        "service": "MSOA Authentication Service",
        "status": "running",
        "port": 8081
    }