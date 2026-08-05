import os
import hashlib
import secrets
import time
import jwt
from fastapi import Header, HTTPException

JWT_ALGO = "HS256"
JWT_EXP_SECONDS = 60 * 60 * 24 * 30  # 30 days

_env_secret = os.getenv("JWT_SECRET")
if not _env_secret:
    print("[auth] WARNING: JWT_SECRET not set — using an ephemeral secret. "
          "Sessions will be invalidated on every restart. Set JWT_SECRET in production.")
JWT_SECRET = _env_secret or secrets.token_hex(32)

PBKDF2_ITERATIONS = 200_000

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ITERATIONS)
    return f"{salt}${digest.hex()}"

def verify_password(password: str, stored: str) -> bool:
    if not stored:
        return False
    try:
        salt, digest_hex = stored.split("$")
    except ValueError:
        return False
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ITERATIONS)
    return secrets.compare_digest(check.hex(), digest_hex)

def create_token(user_id: int, username: str) -> str:
    payload = {"sub": str(user_id), "username": username, "exp": int(time.time()) + JWT_EXP_SECONDS}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired session — please log in again")

async def get_current_user_id(authorization: str = Header(None)) -> int:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization[len("Bearer "):]
    payload = decode_token(token)
    return int(payload["sub"])
