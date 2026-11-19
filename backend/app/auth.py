"""Authentication helpers: password hashing, validation rules, token handling."""
import hashlib
import hmac
import os
import re
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Header, HTTPException
from sqlalchemy.orm import Session

from . import models
from .database import SessionLocal

# ---- Password hashing: PBKDF2-HMAC-SHA256 with per-user random salt (stdlib only) ----
PBKDF2_ROUNDS = 210_000
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${PBKDF2_ROUNDS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, rounds, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(rounds)
        )
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


def validate_username(username: str) -> Optional[str]:
    if not username or not USERNAME_RE.match(username):
        return "用户名需为 3-20 位字母、数字或下划线"
    return None


def validate_password(password: str) -> Optional[str]:
    if not password or len(password) < 8 or len(password) > 32:
        return "密码需为 8-32 位"
    if not re.search(r"[a-z]", password):
        return "密码需包含小写字母"
    if not re.search(r"[A-Z]", password):
        return "密码需包含大写字母"
    if not re.search(r"\d", password):
        return "密码需包含数字"
    return None


def create_token(db: Session, user_id: int, ttl_days: int = 30) -> str:
    token = secrets.token_urlsafe(32)
    rec = models.AuthToken(
        token=token,
        user_id=user_id,
        expires_at=datetime.now() + timedelta(days=ttl_days),
    )
    db.add(rec)
    db.commit()
    return token


def get_current_user(authorization: Optional[str] = Header(None)):
    """FastAPI dependency: require a valid Bearer token."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "未登录或登录已过期")
    token = authorization[7:].strip()
    db = SessionLocal()
    try:
        rec = db.query(models.AuthToken).filter(models.AuthToken.token == token).first()
        if not rec:
            raise HTTPException(401, "无效的登录凭证")
        if rec.expires_at and rec.expires_at < datetime.now():
            raise HTTPException(401, "登录已过期，请重新登录")
        user = db.query(models.User).filter(models.User.id == rec.user_id).first()
        if not user:
            raise HTTPException(401, "用户不存在")
        return {"id": user.id, "username": user.username, "role": user.role}
    finally:
        db.close()
